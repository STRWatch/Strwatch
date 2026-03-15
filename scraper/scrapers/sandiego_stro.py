"""
scrapers/sandiego_stro.py — San Diego STRO license data via Open Data Portal.

Source: https://data.sandiego.gov/datasets/stro-licenses/
CSV download: https://seshat.datasd.org/stro/stro_licenses_datasd.csv

San Diego has a 4-tier STRO license system:
  - Tier 1: Part-time (<20 nights/year)
  - Tier 2: Home-sharing (owner on-site, primary residence)
  - Tier 3: Whole-home (>20 days/year, outside Mission Beach) — capped at 1% of housing
  - Tier 4: Mission Beach whole-home — capped at 30% of area housing

~7,954 active licenses. License fee: $250/year. Non-transferable.
"""

import logging
import requests
import csv
import io
from datetime import datetime, timezone, timedelta
from typing import List

from db import store
from alerts import notify

log = logging.getLogger(__name__)

CSV_URL = "https://seshat.datasd.org/stro/stro_licenses_datasd.csv"
CITY = "San Diego, CA"

HEADERS = {
    "User-Agent": "STRWatch/1.0 (regulatory monitoring; contact@strwatch.io)",
}


def _fetch_csv() -> List[dict]:
    """Download and parse the STRO licenses CSV."""
    try:
        resp = requests.get(CSV_URL, headers=HEADERS, timeout=60)
        resp.raise_for_status()

        reader = csv.DictReader(io.StringIO(resp.text))
        records = list(reader)
        log.info("San Diego CSV: downloaded %d records", len(records))
        return records
    except requests.exceptions.HTTPError as e:
        log.error("San Diego CSV HTTP error: %s", e)
        return []
    except Exception as e:
        log.error("San Diego CSV fetch error: %s", e)
        return []


def _normalize(raw: dict) -> dict:
    """Normalize a CSV row to our standard schema."""
    return {
        "raw": raw,
        "license_id": raw.get("license_id") or raw.get("stro_license_id") or raw.get("account_key") or str(hash(str(raw))),
        "address": (raw.get("street") or raw.get("address") or "").strip(),
        "zip_code": (raw.get("zip") or raw.get("zip_code") or "").strip(),
        "license_type": (raw.get("tier") or raw.get("license_tier") or "").strip(),
        "status": "active",  # CSV only contains active licenses
        "issued_date": (raw.get("account_start_year") or raw.get("start_year") or "").strip(),
        "expiry_date": (raw.get("expiration_year") or raw.get("exp_year") or "").strip(),
        "planning_area": (raw.get("planning_area") or raw.get("cpd") or "").strip(),
        "owner_name": "",  # Not in public dataset
    }


def dump_fields():
    """Print raw field names from the first record. Use to verify field mapping."""
    records = _fetch_csv()
    if not records:
        print("No records returned — check URL or network.")
        return
    record = records[0]
    print("\n=== San Diego STRO CSV — Field Names ===")
    for key, val in record.items():
        print(f"  {key!r:40s} → {str(val)[:60]!r}")
    print(f"\nTotal fields: {len(record)}")
    print(f"Total records: {len(records)}")


def run(full_sync: bool = False):
    """
    Main entry point. Download CSV, normalize, upsert all records.
    
    Since the CSV only contains current active licenses, we always
    do a full comparison — there's no incremental endpoint.
    """
    log.info("=== San Diego STRO scraper starting ===")

    raw_records = _fetch_csv()
    if not raw_records:
        log.error("No records fetched — aborting")
        return {"processed": 0, "new": 0, "errors": 0}

    new_licenses = []
    total_processed = 0
    errors = 0

    # Get current DB license IDs to detect removals
    current_db_ids = set()
    try:
        current_db_ids = store.get_sandiego_license_ids()
    except Exception:
        pass  # First run, table may not exist yet

    csv_ids = set()

    for raw in raw_records:
        total_processed += 1
        record = _normalize(raw)
        csv_ids.add(record["license_id"])

        try:
            result = store.upsert_sandiego_license(record)
            if result["is_new"]:
                new_licenses.append(record)
                log.debug("New SD license: %s @ %s (Tier %s)",
                          record["license_id"], record["address"], record["license_type"])
        except Exception as e:
            errors += 1
            log.error("Error processing SD record %s: %s", record.get("license_id"), e)

    # Detect removed licenses (in DB but not in current CSV)
    removed_ids = current_db_ids - csv_ids
    removed_licenses = []
    for lid in removed_ids:
        try:
            store.mark_sandiego_license_removed(lid)
            removed_licenses.append({"license_id": lid})
        except Exception as e:
            log.error("Error marking removal for %s: %s", lid, e)

    stats = store.get_sandiego_stats()
    log.info(
        "San Diego STRO complete — processed: %d | new: %d | removed: %d | errors: %d | db total: %d",
        total_processed, len(new_licenses), len(removed_licenses), errors, stats.get("total", 0)
    )

    # Alerts
    if new_licenses:
        notify.alert_sandiego_new_licenses(new_licenses)

    if removed_licenses:
        notify.alert_sandiego_removals(removed_licenses)

    return {
        "processed": total_processed,
        "new": len(new_licenses),
        "removed": len(removed_licenses),
        "errors": errors,
        "stats": stats,
    }


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.DEBUG)
    if "--dump-fields" in sys.argv:
        dump_fields()
    else:
        result = run()
        print(f"\nResult: {result}")
