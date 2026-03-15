"""
scrapers/miamibeach_web.py — Miami Beach STR page monitoring.

Miami Beach has the most aggressive STR enforcement in the US:
  - $20,000 fine for first offense (operating without BTR)
  - Each subsequent offense increases by $20,000 (up to $100K+)
  - Only legal in specific zoning districts (NOT in single-family residential)
  - Requires: FL DBPR vacation rental license, Business Tax Receipt,
    Resort Tax Certificate, Miami-Dade Certificate of Use
  - Tenants/visitors evicted from illegal STRs
  - City has "Practice Safe Renting" portal for public lookup
  - Must display BTR and Resort Tax numbers on all listings

Data sources:
  - City STR page: miamibeachfl.gov/business/vacation-short-term-rentals/
  - STR requirements: miamibeachfl.gov/short-term-rental-requirements/
  - Practice Safe Renting lookup: apps.miamibeachfl.gov/practicesaferenting
  - Miami-Dade County STR: miamidade.gov/building/standards/residential-short-term-vacation-rentals.asp
"""

import logging
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)

CITY = "Miami Beach, FL"

WATCHED_PAGES = [
    {
        "name": "Miami Beach — Vacation/Short-Term Rentals",
        "url": "https://www.miamibeachfl.gov/business/vacation-short-term-rentals/",
        "priority": "high",
    },
    {
        "name": "Miami Beach — STR Requirements",
        "url": "https://www.miamibeachfl.gov/short-term-rental-requirements/",
        "priority": "high",
    },
    {
        "name": "Miami Beach — Practice Safe Renting Portal",
        "url": "https://apps.miamibeachfl.gov/practicesaferenting",
        "priority": "medium",
    },
    {
        "name": "Miami-Dade County — STR Regulations",
        "url": "https://www.miamidade.gov/building/standards/residential-short-term-vacation-rentals.asp",
        "priority": "medium",
    },
]


def run():
    """Watch Miami Beach STR regulation pages for changes."""
    log.info("=== Miami Beach page watcher starting ===")

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

    log.info("Miami Beach page watcher done — checked: %d | changed: %d",
             len(WATCHED_PAGES), changes)

    return {
        "checked": len(WATCHED_PAGES),
        "changes": changes,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    result = run()
    print(f"\nResult: {result}")
