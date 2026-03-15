"""
scrapers/charleston_web.py — Charleston SC STR page monitoring.

Charleston has strict STR zoning:
  - Peninsula: accessory unit only, owner must be primary resident and present
  - Whole-home rentals only in commercial zones
  - ~700 active permits, annual renewal required, non-transferable
  - Actively enforced with fines

Data sources:
  - ArcGIS open data portal: data-charleston-sc.opendata.arcgis.com
  - STR permit info: charleston-sc.gov/1840/Short-Term-Rental-Permit-Information
  - STR ordinance: charleston-sc.gov/2529/Short-Term-Rental-Ordinance
"""

import logging
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)

CITY = "Charleston, SC"

WATCHED_PAGES = [
    {
        "name": "Charleston — STR Permit Information",
        "url": "https://www.charleston-sc.gov/1840/Short-Term-Rental-Permit-Information",
        "priority": "high",
    },
    {
        "name": "Charleston — STR Ordinance & Task Force",
        "url": "https://www.charleston-sc.gov/2529/Short-Term-Rental-Ordinance",
        "priority": "high",
    },
    {
        "name": "Charleston — Open Data Portal",
        "url": "https://data-charleston-sc.opendata.arcgis.com/",
        "priority": "low",
    },
]


def run():
    """Watch Charleston STR regulation pages for changes."""
    log.info("=== Charleston page watcher starting ===")

    changes = 0
    for page in WATCHED_PAGES:
        try:
            changed = watch_page(
                name=page["name"],
                url=page["url"],
                city=CITY,
                priority=page["priority"],
            )
            if changed:
                changes += 1
        except Exception as e:
            log.error("Error watching %s: %s", page["name"], e)

    log.info("Charleston page watcher done — checked: %d | changed: %d",
             len(WATCHED_PAGES), changes)

    return {
        "checked": len(WATCHED_PAGES),
        "changes": changes,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    result = run()
    print(f"\nResult: {result}")
