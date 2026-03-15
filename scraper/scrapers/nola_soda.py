"""
scrapers/nola_soda.py — New Orleans STR license data via Data.NOLA.gov (SODA API).

Datasets:
  - Non-Commercial STR Licenses: https://data.nola.gov/resource/2ei9-wqw2.json
  - STR Permit Applications:     https://data.nola.gov/resource/en36-xvxg.json

New Orleans has multiple permit types:
  - Residential (Partial-Unit, Small, Large)
  - Commercial
  - Operator permits
  - Platform permits

This scraper focuses on active license data, detects new licenses,
revocations/expirations, and status changes.
"""

import logging
import requests
from datetime import datetime, timezone, timedelta
from typing import Iterator, List, Optional

from db import store
from alerts import notify

log = logging.getLogger(__name__)

# Primary dataset: Non-Commercial STR Licenses
ENDPOINT = "https://data.nola.gov/resource/2ei9-wqw2.json"
# Secondary: All STR permit applications
APPLICATIONS_ENDPOINT = "https://data.nola.gov/resource/en36-xvxg.json"

PAGE_SIZE = 1000
CITY = "New Orleans, LA"

# Field mapping — verified via --dump-fields on 2026-03-15
FIELD_MAP = {
    "license_number":       "license_id",
    "licid":                "licid",
    "reference_code":       "reference_code",
    "address":              "address",
    "type":                 "license_type",
    "current_status":       "status",
    "issue_date":           "issued_date",
    "expiration_date":      "expiry_date",
    "owner":                "owner_name",
    "operator":             "operator_name",
    "operator_type":        "operator_type",
    "operator_phone":       "operator_phone",
    "operator_email":       "operator_email",
    "type_of_building":     "building_type",
    "bedrooms_rented":      "bedroom_limit",
    "max_occupancy":        "guest_limit",
    "partial_whole":        "partial_whole",
    "operator_permit":      "operator_permit",
}


def _normalize(raw: dict) -> dict:
    """Map raw SODA record to our normalized schema using verified field names."""
    return {
        "raw": raw,
        "license_id": raw.get("license_number") or raw.get("licid") or str(hash(str(raw))),
        "address": raw.get("address") or "",
        "license_type": raw.get("type") or "",
        "status": raw.get("current_status") or "",
        "issued_date": (raw.get("issue_date") or "")[:10],
        "expiry_date": (raw.get("expiration_date") or "")[:10],
        "owner_name": raw.get("owner") or "",
        "neighborhood": "",  # not in this dataset
        "bedroom_limit": raw.get("bedrooms_rented") or "",
        "guest_limit": raw.get("max_occupancy") or "",
        "building_type": raw.get("type_of_building") or "",
        "partial_whole": raw.get("partial_whole") or "",
        "operator_name": raw.get("operator") or "",
    }


def _fetch_page(endpoint: str, offset: int, since: Optional[str] = None) -> List[dict]:
    """Fetch one page of records from SODA API."""
    params = {
        "$limit": PAGE_SIZE,
        "$offset": offset,
        "$order": ":updated_at DESC",
    }
    if since:
        params["$where"] = f":updated_at > '{since}'"

    headers = {
        "Accept": "application/json",
        "User-Agent": "STRWatch/1.0 (regulatory monitoring; contact@strwatch.io)",
    }
    try:
        resp = requests.get(endpoint, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        log.error("NOLA SODA API HTTP error: %s", e)
        return []
    except requests.exceptions.ConnectionError as e:
        log.error("NOLA SODA API connection error: %s", e)
        return []
    except Exception as e:
        log.error("NOLA SODA API unexpected error: %s", e)
        return []


def fetch_all(since: Optional[str] = None) -> Iterator[dict]:
    """
    Yield all normalized license records, paginating through SODA API.
    If `since` is provided (ISO datetime string), only fetches recently updated records.
    """
    offset = 0
    total_fetched = 0
    while True:
        log.debug("Fetching NOLA SODA page offset=%d since=%s", offset, since)
        page = _fetch_page(ENDPOINT, offset, since)
        if not page:
            break
        for raw in page:
            yield _normalize(raw)
            total_fetched += 1
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    log.info("NOLA SODA: fetched %d records (since=%s)", total_fetched, since or "all time")


def dump_fields():
    """Print raw field names from the first record. Use to verify FIELD_MAP."""
    page = _fetch_page(ENDPOINT, 0)
    if not page:
        print("No records returned — check endpoint or network.")
        return
    record = page[0]
    print("\n=== NOLA SODA API — Field Names ===")
    for key, val in record.items():
        print(f"  {key!r:40s} → {str(val)[:60]!r}")
    print(f"\nTotal fields: {len(record)}")
    print("\nUpdate FIELD_MAP in nola_soda.py to match these field names.")


def run(full_sync: bool = False):
    """
    Main entry point. Called by run.py.

    Args:
        full_sync: If True, fetches all records regardless of last run time.
    """
    log.info("=== New Orleans SODA scraper starting (full_sync=%s) ===", full_sync)

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
            result = store.upsert_nola_license(record)

            if result["is_new"]:
                new_licenses.append(record)
                log.debug("New NOLA license: %s @ %s", record.get("license_id"), record.get("address"))

            if result["was_revoked"]:
                revoked_licenses.append(record)
                log.info("NOLA Revocation: %s @ %s (status: %s)",
                         record.get("license_id"), record.get("address"), record.get("status"))

        except Exception as e:
            errors += 1
            log.error("Error processing NOLA record %s: %s", record.get("license_id"), e)

    stats = store.get_nola_stats()
    log.info(
        "NOLA SODA complete — processed: %d | new: %d | revoked: %d | errors: %d | db total: %d active: %d",
        total_processed, len(new_licenses), len(revoked_licenses), errors,
        stats.get("total", 0), stats.get("active", 0)
    )

    # Alerts
    if new_licenses:
        notify.alert_nola_new_licenses(new_licenses)

    if revoked_licenses:
        notify.alert_nola_revocations(revoked_licenses)

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
    elif "--full" in sys.argv:
        result = run(full_sync=True)
        print(f"\nResult: {result}")
    else:
        result = run(full_sync=False)
        print(f"\nResult: {result}")
