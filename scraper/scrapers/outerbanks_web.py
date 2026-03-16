"""
scrapers/outerbanks_web.py — Outer Banks NC STR page monitoring.

Outer Banks is one of the oldest and largest vacation rental markets in the US:
  - Multiple jurisdictions: Dare County, Currituck County, Kill Devil Hills,
    Nags Head, Kitty Hawk, Duck, Southern Shores, Manteo
  - Generally STR-friendly but increasing regulation
  - NC state preemption limits some local restrictions
  - 6.75% state sales tax + local occupancy tax (varies 5-6%)
  - Safety inspections increasingly required
  - Septic/well capacity limits occupancy in many areas
"""

import logging
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)
CITY = "Outer Banks, NC"

WATCHED_PAGES = [
    {"name": "Dare County — Rental Cottage Info", "url": "https://www.darenc.com/departments/planning/rental-cottage-compliance", "priority": "high"},
    {"name": "Kill Devil Hills — Vacation Rentals", "url": "https://www.kdhnc.com/378/Vacation-Rental-Program", "priority": "high"},
    {"name": "Nags Head — Cottage Rentals", "url": "https://www.nagsheadnc.gov/314/Rental-Cottage-Information", "priority": "medium"},
]

def run():
    log.info("=== Outer Banks page watcher starting ===")
    changes = 0
    for page in WATCHED_PAGES:
        try:
            if watch_page(page["name"], page["url"], CITY, page["priority"]):
                changes += 1
        except Exception as e:
            log.error("Error watching %s: %s", page["name"], e)
    log.info("Outer Banks page watcher done — checked: %d | changed: %d", len(WATCHED_PAGES), changes)
    return {"checked": len(WATCHED_PAGES), "changes": changes}

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print(run())
