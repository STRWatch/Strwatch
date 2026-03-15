"""
scrapers/asheville_web.py — Asheville NC STR page monitoring.

Asheville has some of the strictest STR regulations in the Southeast:
  - Whole-home STRs banned in all residential zones since 2018
  - Only "homestays" allowed: owner-present, max 2 bedrooms, <30 days
  - STRs only permitted in commercially zoned or "resort" zoned areas
  - New whole-home STRs require conditional zoning approval from City Council
  - Homestay permit: ~$208 application fee, annual renewal
  - Active enforcement: dedicated STR enforcement employee
  - 30-day cure period after notice of violation
  - Buncombe County (outside city limits) much more permissive — no permit required
  - Taxes: 6.75% state sales + local occupancy tax

Data sources:
  - City STR info: ashevillenc.gov/service/apply-for-a-homestay-permit/
  - City news/enforcement: ashevillenc.gov (STR updates)
  - City Development Services: ashevillenc.gov/department/development-services/
"""

import logging
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)

CITY = "Asheville, NC"

WATCHED_PAGES = [
    {
        "name": "Asheville — Homestay Permit Application",
        "url": "https://www.ashevillenc.gov/service/apply-for-a-homestay-permit/",
        "priority": "high",
    },
    {
        "name": "Asheville — STR Regulation Update & Enforcement",
        "url": "https://www.ashevillenc.gov/news/asheville-homestay-and-short-term-rental-update-regulation-changes-and-active-enforcement/",
        "priority": "high",
    },
    {
        "name": "Asheville — Development Services",
        "url": "https://www.ashevillenc.gov/department/development-services/",
        "priority": "medium",
    },
]


def run():
    """Watch Asheville STR regulation pages for changes."""
    log.info("=== Asheville page watcher starting ===")

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

    log.info("Asheville page watcher done — checked: %d | changed: %d",
             len(WATCHED_PAGES), changes)

    return {
        "checked": len(WATCHED_PAGES),
        "changes": changes,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    result = run()
    print(f"\nResult: {result}")
