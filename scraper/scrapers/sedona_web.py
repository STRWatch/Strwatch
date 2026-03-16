"""
scrapers/sedona_web.py — Sedona AZ STR page monitoring.

Sedona has seen explosive STR growth (400 → 1,200+ permits since 2020):
  - Annual STR permit required from City of Sedona
  - AZ Transaction Privilege Tax (TPT) license required from state
  - Late renewal fees: $50 (2-90 days late), $100 (90+ days late) — effective Jan 2026
  - No special events allowed at STRs (weddings, conferences, etc.)
  - Sex offender background check required on all guests
  - Neighbor notification required for adjacent properties
  - 24/7 emergency contact who can respond within 60 minutes
  - Permit number displayed on all advertisements
  - 24/7 complaint hotline: 928-203-5110
  - Tax rates: ~13.3% (Yavapai) or ~13.9% (Coconino) depending on county
  - ~20% of Sedona housing is STR, 66% owned by non-residents
  - City declared housing shortage emergency

Data sources:
  - City STR page: sedonaaz.gov/vacation-rentals
  - STR FAQ: sedonaaz.gov/vacation-rentals-faqs
  - Pending legislation: sedonaaz.gov/pending-legislation
  - City code: sedona.municipal.codes/SCC/5.25
"""

import logging
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)

CITY = "Sedona, AZ"

WATCHED_PAGES = [
    {
        "name": "Sedona — Short-Term Rentals Main Page",
        "url": "https://www.sedonaaz.gov/your-government/departments/community-development/vacation-rentals",
        "priority": "high",
    },
    {
        "name": "Sedona — STR FAQs",
        "url": "https://www.sedonaaz.gov/your-government/departments/community-development/vacation-rentals/vacation-rentals-faqs",
        "priority": "high",
    },
    {
        "name": "Sedona — Pending STR Legislation",
        "url": "https://www.sedonaaz.gov/your-government/departments/community-development/vacation-rentals/pending-legislation",
        "priority": "high",
    },
]


def run():
    """Watch Sedona STR regulation pages for changes."""
    log.info("=== Sedona page watcher starting ===")

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

    log.info("Sedona page watcher done — checked: %d | changed: %d",
             len(WATCHED_PAGES), changes)

    return {
        "checked": len(WATCHED_PAGES),
        "changes": changes,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    result = run()
    print(f"\nResult: {result}")
