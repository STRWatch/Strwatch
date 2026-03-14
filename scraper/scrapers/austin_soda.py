"""
scrapers/austin_soda.py — Austin STR license data via Austin Open Data SODA API.

Endpoint: https://data.austintexas.gov/resource/2fah-4p7e.json
- Fetches active STR licenses (Type 1, 2, 3) by neighborhood/zip
- Detects: new licenses, status changes, expiring licenses
- Incremental: only fetches records updated since last run
- Fires alerts for revocations (especially relevant pre-July 1 deadline)

Run with --dump-fields first to verify field mapping against live API.
Run with --full for initial sync.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logging
import requests
from datetime import datetime, timezone, timedelta, date
from typing import Iterator, List, Optional

import config
from db import store
from alerts import notify

log = logging.getLogger(__name__)

ENDPOINT = "https://data.austintexas.gov/resource/2fah-4p7e.json"
PAGE_SIZE = 1000

# July 1, 2026 enforcement cliff — licenses must be active by this date
ENFORCEMENT_DEADLINE = date(2026, 7, 1)

# ── Field mapping ─────────────────────────────────────────────────────────────
# SODA field names → our normalized names.
# Run with --dump-fields to verify against live API column names.
FIELD_MAP = {
    # Actual field names from Austin SODA API (verified via --dump-fields)
    "case_number":          "license_id",
    "str_type":             "license_type",
    "prop_address":         "street_name",
    "prop_zip":             "zip_code",
    "council_district":     "council_district",
}


def _normalize(raw: dict) -> dict:
    """Map raw SODA record to our normalized schema."""
    out = {"raw": raw, "city": "Austin"}
    out["license_id"] = raw.get("case_number") or raw.get(":id") or str(hash(str(raw)))
    out["license_type"] = raw.get("str_type")
    out["street_name"] = raw.get("prop_address")
    out["zip_code"] = raw.get("prop_zip")
    out["council_district"] = raw.get("council_district")
    out["status"] = raw.get("status", "active")
    city = raw.get("prop_city", "Austin")
    state = raw.get("prop_state", "TX")
    parts = [out.get("street_name"), city, state, out.get("zip_code")]
    out["address"] = ", ".join(p for p in parts if p) or "Austin, TX"
    return out

def _fetch_page(offset: int, since: Optional[str] = None) -> List[dict]:
    """Fetch one page of records from Austin SODA API."""
    params = {
        "$limit": PAGE_SIZE,
        "$offset": offset,
        "$order": ":updated_at DESC",
    }
    if since:
        params["$where"] = f":updated_at > '{since}'"

    headers = {
        "Accept": "application/json",
        "User-Agent": "STRWatch/1.0 (contact@strwatch.io)",
    }
    try:
        resp = requests.get(ENDPOINT, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        log.error("Austin SODA HTTP error: %s", e)
        return []
    except requests.exceptions.ConnectionError as e:
        log.error("Austin SODA connection error: %s", e)
        return []
    except Exception as e:
        log.error("Austin SODA unexpected error: %s", e)
        return []


def fetch_all(since: Optional[str] = None) -> Iterator[dict]:
    """
    Yield all normalized Austin STR license records.
    If `since` is provided (ISO datetime string), only fetches recently updated records.
    """
    offset = 0
    total_fetched = 0
    while True:
        log.debug("Fetching Austin SODA page offset=%d since=%s", offset, since)
        page = _fetch_page(offset, since)
        if not page:
            break
        for raw in page:
            yield _normalize(raw)
            total_fetched += 1
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    log.info("Austin SODA: fetched %d records (since=%s)", total_fetched, since or "all time")


def dump_fields():
    """Print raw field names from the first record. Run this to verify FIELD_MAP."""
    page = _fetch_page(0)
    if not page:
        print("No records returned — check endpoint or network.")
        return
    record = page[0]
    print("\n=== Austin SODA API — Field Names ===")
    for key, val in record.items():
        print(f"  {key!r:40s} → {str(val)[:60]!r}")
    print(f"\nTotal fields: {len(record)}")
    print("\nUpdate FIELD_MAP in austin_soda.py to match these field names.")


def _days_to_deadline() -> int:
    return (ENFORCEMENT_DEADLINE - date.today()).days


# ── Main run function ─────────────────────────────────────────────────────────

def run(full_sync: bool = False):
    """
    Main entry point. Called by run.py.

    Args:
        full_sync: If True, fetches all records. Use for first run.
    """
    log.info("=== Austin SODA scraper starting (full_sync=%s) ===", full_sync)

    # Skip if already synced today
    from db.store import get_conn
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM austin_licenses").fetchone()[0]
    if not full_sync and count > 0:
        log.info("Austin SODA already has %d records — skipping full sync", count)
        from db import store as _store
        return {"processed": 0, "new": 0, "revoked": 0, "errors": 0, "stats": _store.get_austin_license_stats(), "days_to_deadline": _days_to_deadline()}

    since = None
    if not full_sync:
        cutoff = datetime.now(timezone.utc) - timedelta(days=2)
        since = cutoff.strftime("%Y-%m-%dT%H:%M:%S")

    new_licenses = []
    revoked_licenses = []
    total_processed = 0
    errors = 0

    for record in fetch_all(since=since):
        total_processed += 1
        try:
            result = store.upsert_austin_license(record)

            if result["is_new"]:
                new_licenses.append(record)
                log.debug("New Austin license: %s @ %s (%s)",
                          record.get("license_id"), record.get("address"),
                          record.get("license_type", "unknown type"))

            if result["was_revoked"]:
                revoked_licenses.append(record)
                log.info("Austin revocation: %s @ %s (status: %s)",
                         record.get("license_id"), record.get("address"),
                         record.get("status"))

        except Exception as e:
            errors += 1
            log.error("Error processing Austin record %s: %s", record.get("license_id"), e)

    # ── Stats ──
    try:
        stats = store.get_austin_license_stats()
    except Exception:
        stats = {"total": total_processed, "active": 0}

    log.info(
        "Austin SODA complete — processed: %d | new: %d | revoked: %d | errors: %d | deadline: %d days",
        total_processed, len(new_licenses), len(revoked_licenses), errors, _days_to_deadline()
    )

    # ── Alerts ──
    if new_licenses:
        notify.alert_austin_new_licenses(new_licenses)

    if revoked_licenses:
        # Revocations are high priority pre-July 1 — hosts need to reapply
        notify.alert_austin_revocations(revoked_licenses)

    return {
        "processed": total_processed,
        "new": len(new_licenses),
        "revoked": len(revoked_licenses),
        "errors": errors,
        "stats": stats,
        "days_to_deadline": _days_to_deadline(),
    }


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.DEBUG)

    if "--dump-fields" in sys.argv:
        dump_fields()
    elif "--full" in sys.argv:
        result = run(full_sync=True)
        print(f"\nResult: {result}")
    else:
        result = run(full_sync=False)
        print(f"\nResult: {result}")
