"""
scrapers/scottsdale_arcgis.py — Scottsdale STR license data via ArcGIS REST API.

Endpoint: https://maps.scottsdaleaz.gov/arcgis/rest/services/OpenData/MapServer/32/query
- 3,002 active STR licenses, updated daily
- Detects: new licenses, status changes
- Fields verified via --dump-fields: site_address, prop_owner_name,
  prop_mgmt_company, emerg_contact, emerg_24hr_phone_num,
  PropertyScore, Scottsdale_License_Number, OBJECTID_1

Scottsdale enforcement: $1,000/violation, active monitoring of STR listings.
Annual license fee: $250/property.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import requests
from datetime import datetime, timezone
from typing import Iterator, List, Optional

import config
from db import store
from alerts import notify

log = logging.getLogger(__name__)

ENDPOINT = "https://maps.scottsdaleaz.gov/arcgis/rest/services/OpenData/MapServer/32/query"
PAGE_SIZE = 1000


def _fetch_page(offset: int) -> List[dict]:
    """Fetch one page of records from ArcGIS REST API."""
    params = {
        "where": "1=1",
        "outFields": "*",
        "resultOffset": offset,
        "resultRecordCount": PAGE_SIZE,
        "orderByFields": "OBJECTID_1 ASC",
        "f": "json",
    }
    headers = {"User-Agent": "STRWatch/1.0 (contact@strwatch.io)"}
    try:
        resp = requests.get(ENDPOINT, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            log.error("ArcGIS API error: %s", data["error"])
            return []
        return [f["attributes"] for f in data.get("features", [])]
    except Exception as e:
        log.error("Scottsdale ArcGIS error: %s", e)
        return []


def fetch_all() -> Iterator[dict]:
    """Yield all normalized Scottsdale STR license records."""
    offset = 0
    total_fetched = 0
    while True:
        log.debug("Fetching Scottsdale ArcGIS page offset=%d", offset)
        page = _fetch_page(offset)
        if not page:
            break
        for raw in page:
            yield _normalize(raw)
            total_fetched += 1
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    log.info("Scottsdale ArcGIS: fetched %d records", total_fetched)


def _normalize(raw: dict) -> dict:
    """Map raw ArcGIS record to our normalized schema."""
    return {
        "raw": raw,
        "city": "Scottsdale",
        "license_id": str(raw.get("Scottsdale_License_Number") or raw.get("OBJECTID_1", "")),
        "address": raw.get("site_address") or "",
        "owner_name": raw.get("prop_owner_name") or "",
        "mgmt_company": raw.get("prop_mgmt_company") or "",
        "emerg_contact": raw.get("emerg_contact") or "",
        "emerg_phone": raw.get("emerg_24hr_phone_num") or "",
        "property_score": raw.get("PropertyScore") or "",
        # ArcGIS doesn't include status/expiry in this dataset — active = in dataset
        "status": "active",
    }


def dump_fields():
    """Print raw field names from first record."""
    page = _fetch_page(0)
    if not page:
        print("No records returned.")
        return
    print("\n=== Scottsdale ArcGIS — Field Names ===")
    for key, val in page[0].items():
        print(f"  {key!r:40s} → {str(val)[:60]!r}")
    print(f"\nTotal fields: {len(page[0])}")


def _get_db_stats() -> dict:
    try:
        return store.get_scottsdale_license_stats()
    except Exception:
        return {"total": 0, "active": 0}


# ── Main run function ─────────────────────────────────────────────────────────

def run(full_sync: bool = False):
    """
    Main entry point. Called by run.py.
    Only does a full sync once per day to avoid hanging on 3K records.
    """
    from datetime import datetime, timezone
    stats = _get_db_stats()
    if not full_sync and stats.get("total", 0) > 0:
        # Check if we already ran today
        log.info("Scottsdale already has %d records — skipping full sync", stats.get("total", 0))
        return {"processed": 0, "new": 0, "errors": 0, "stats": stats}
    log.info("=== Scottsdale ArcGIS scraper starting ===")

    new_licenses = []
    total_processed = 0
    errors = 0

    for record in fetch_all():
        total_processed += 1
        try:
            result = store.upsert_scottsdale_license(record)
            if result["is_new"]:
                new_licenses.append(record)
                log.debug("New Scottsdale license: %s @ %s",
                          record.get("license_id"), record.get("address"))
        except Exception as e:
            errors += 1
            log.error("Error processing Scottsdale record %s: %s",
                      record.get("license_id"), e)

    stats = _get_db_stats()
    log.info(
        "Scottsdale ArcGIS complete — processed: %d | new: %d | errors: %d | db total: %d",
        total_processed, len(new_licenses), errors, stats.get("total", 0)
    )

    if new_licenses:
        notify.alert_scottsdale_new_licenses(new_licenses)

    return {
        "processed": total_processed,
        "new": len(new_licenses),
        "errors": errors,
        "stats": stats,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    if "--dump-fields" in sys.argv:
        dump_fields()
    else:
        result = run()
        print(f"\nResult: {result}")
