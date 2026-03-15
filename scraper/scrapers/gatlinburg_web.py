"""
scrapers/gatlinburg_web.py — Gatlinburg TN STR page monitoring.

Gatlinburg is one of the highest STR-density markets in the US:
  - Called "Tourist Residences" locally
  - Tourist Residency (TR) Permit required: $200 base + $75/extra bedroom
  - City + County business licenses ($15 each)
  - Prohibited in R-1A and R-2A residential zones
  - Annual fire/safety inspections required
  - Max occupancy: 2x bedrooms + 4, capped at 12
  - Taxes: 9.75% sales + 3% lodging = 12.75%
  - Sevier County STRU permit required outside city limits (since Jan 2024)
  - Non-owner properties classified as commercial (40% tax rate)

Note: gatlinburgtn.gov uses aggressive bot protection (406/403 on main pages).
We monitor the PDF document and old-style PHP URLs which are accessible,
plus the Sevier County site.
"""

import logging
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)

CITY = "Gatlinburg, TN"

WATCHED_PAGES = [
    {
        "name": "Gatlinburg — Overnight Rental Info (PDF)",
        "url": "https://www.gatlinburgtn.gov/Finance/New%20Business%20Overnight%20Rental.pdf",
        "priority": "high",
    },
    {
        "name": "Gatlinburg — Planning Documents & Zoning",
        "url": "https://www.gatlinburgtn.gov/departments/planning/planning_documents___information.php",
        "priority": "medium",
    },
    {
        "name": "Sevier County — STR Inspection Program",
        "url": "https://www.seviercountytn.gov/fire_prevention/stru_inspection_program.php",
        "priority": "high",
    },
]


def run():
    """Watch Gatlinburg STR regulation pages for changes."""
    log.info("=== Gatlinburg page watcher starting ===")

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

    log.info("Gatlinburg page watcher done — checked: %d | changed: %d",
             len(WATCHED_PAGES), changes)

    return {
        "checked": len(WATCHED_PAGES),
        "changes": changes,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    result = run()
    print(f"\nResult: {result}")
