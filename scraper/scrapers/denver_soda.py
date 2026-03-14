"""
scrapers/denver_soda.py — Denver STR license data via Colorado SODA API.

Endpoint: https://data.colorado.gov/resource/f3vc-vat3.json
- Fetches all licenses, compares to local DB
- Detects: new licenses, status changes (revocations/expirations)
- Incremental: only fetches records updated since last run
- Fires alerts for new licenses and revocations
"""

import logging
import requests
from datetime import datetime, timezone, timedelta
from typing import Iterator, List, Optional

import config
from db import store
from alerts import notify

log = logging.getLogger(__name__)

ENDPOINT = config.DENVER_SODA_ENDPOINT
PAGE_SIZE = config.DENVER_SODA_LIMIT

# ── Field mapping ─────────────────────────────────────────────────────────────
# SODA field names → our normalized names.
# Run with --dump-fields to discover the actual column names for this dataset.
FIELD_MAP = {
    # Common SODA field names for Denver STR dataset — adjust after --dump-fields
    "licensenumber":        "license_id",
    "license_number":       "license_id",
    "licensenum":           "license_id",
    "address":              "address",
    "full_address":         "address",
    "licensetype":          "license_type",
    "license_type":         "license_type",
    "type":                 "license_type",
    "status":               "status",
    "licensestatus":        "status",
    "license_status":       "status",
    "issueddate":           "issued_date",
    "issued_date":          "issued_date",
    "issuedate":            "issued_date",
    "expirationdate":       "expiry_date",
    "expiration_date":      "expiry_date",
    "expiry_date":          "expiry_date",
    "ownername":            "owner_name",
    "owner_name":           "owner_name",
    "applicant_name":       "owner_name",
    "neighborhood":         "neighborhood",
    "neighborhoodname":     "neighborhood",
    "neighborhood_name":    "neighborhood",
}


def _normalize(raw: dict) -> dict:
    """Map raw SODA record to our normalized schema."""
    out = {"raw": raw}
    raw_lower = {k.lower().replace(" ", "_"): v for k, v in raw.items()}
    for soda_field, our_field in FIELD_MAP.items():
        if soda_field in raw_lower and our_field not in out:
            out[our_field] = str(raw_lower[soda_field]).strip() if raw_lower[soda_field] else None
    # Ensure license_id always present (fallback to row number)
    if not out.get("license_id"):
        out["license_id"] = raw.get(":id") or raw.get("_id") or str(hash(str(raw)))
    return out


def _fetch_page(offset: int, since: Optional[str] = None) -> List[dict]:
    """Fetch one page of records from SODA API."""
    params = {
        "$limit": PAGE_SIZE,
        "$offset": offset,
        "$order": ":updated_at DESC",
    }
    if since:
        params["$where"] = f":updated_at > '{since}'"

    headers = {"Accept": "application/json"}
    try:
        resp = requests.get(ENDPOINT, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        log.error("SODA API HTTP error: %s", e)
        return []
    except requests.exceptions.ConnectionError as e:
        log.error("SODA API connection error: %s", e)
        return []
    except Exception as e:
        log.error("SODA API unexpected error: %s", e)
        return []


def fetch_all(since: Optional[str] = None) -> Iterator[dict]:
    """
    Yield all normalized license records, paginating through SODA API.
    If `since` is provided (ISO datetime string), only fetches recently updated records.
    """
    offset = 0
    total_fetched = 0
    while True:
        log.debug("Fetching SODA page offset=%d since=%s", offset, since)
        page = _fetch_page(offset, since)
        if not page:
            break
        for raw in page:
            yield _normalize(raw)
            total_fetched += 1
        if len(page) < PAGE_SIZE:
            break  # Last page
        offset += PAGE_SIZE

    log.info("Denver SODA: fetched %d records (since=%s)", total_fetched, since or "all time")


def dump_fields():
    """Print the raw field names from the first record. Use this to verify FIELD_MAP."""
    page = _fetch_page(0)
    if not page:
        print("No records returned — check endpoint or network.")
        return
    record = page[0]
    print("\n=== Denver SODA API — Field Names ===")
    for key, val in record.items():
        print(f"  {key!r:40s} → {str(val)[:60]!r}")
    print(f"\nTotal fields: {len(record)}")
    print("\nUpdate FIELD_MAP in denver_soda.py to match these field names.")


def get_dataset_metadata() -> dict:
    """Fetch dataset metadata to understand structure and last update time."""
    meta_url = ENDPOINT.replace(".json", "")
    try:
        resp = requests.get(
            f"https://data.colorado.gov/api/views/f3vc-vat3",
            timeout=15
        )
        resp.raise_for_status()
        meta = resp.json()
        return {
            "name": meta.get("name"),
            "row_count": meta.get("cachedContents", {}).get("cardinality"),
            "updated_at": meta.get("rowsUpdatedAt"),
            "columns": [c.get("fieldName") for c in meta.get("columns", [])],
        }
    except Exception as e:
        log.warning("Could not fetch metadata: %s", e)
        return {}


# ── Main run function ─────────────────────────────────────────────────────────

def run(full_sync: bool = False):
    """
    Main entry point. Called by run.py.

    Args:
        full_sync: If True, fetches all records regardless of last run time.
                   Use for first run or to re-sync everything.
    """
    log.info("=== Denver SODA scraper starting (full_sync=%s) ===", full_sync)

    # Determine incremental window
    since = None
    if not full_sync:
        # Look back 2 days to catch anything missed
        cutoff = datetime.now(timezone.utc) - timedelta(days=2)
        since = cutoff.strftime("%Y-%m-%dT%H:%M:%S")

    new_licenses = []
    revoked_licenses = []
    total_processed = 0
    errors = 0

    for record in fetch_all(since=since):
        total_processed += 1
        try:
            result = store.upsert_denver_license(record)

            if result["is_new"]:
                new_licenses.append(record)
                log.debug("New license: %s @ %s", record.get("license_id"), record.get("address"))

            if result["was_revoked"]:
                revoked_licenses.append(record)
                log.info("Revocation: %s @ %s (status: %s)",
                         record.get("license_id"), record.get("address"), record.get("status"))

        except Exception as e:
            errors += 1
            log.error("Error processing record %s: %s", record.get("license_id"), e)

    # ── Summary ──
    stats = store.get_denver_stats()
    log.info(
        "Denver SODA complete — processed: %d | new: %d | revoked: %d | errors: %d | db total: %d active: %d",
        total_processed, len(new_licenses), len(revoked_licenses), errors,
        stats["total"], stats["active"]
    )

    # ── Alerts ──
    if new_licenses:
        notify.alert_denver_new_licenses(new_licenses)

    if revoked_licenses:
        notify.alert_denver_revocations(revoked_licenses)

    return {
        "processed": total_processed,
        "new": len(new_licenses),
        "revoked": len(revoked_licenses),
        "errors": errors,
        "stats": stats,
    }


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.DEBUG)

    if "--dump-fields" in sys.argv:
        dump_fields()
    elif "--meta" in sys.argv:
        meta = get_dataset_metadata()
        print("\n=== Dataset Metadata ===")
        for k, v in meta.items():
            print(f"  {k}: {v}")
    elif "--full" in sys.argv:
        result = run(full_sync=True)
        print(f"\nResult: {result}")
    else:
        result = run(full_sync=False)
        print(f"\nResult: {result}")
