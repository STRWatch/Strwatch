"""
scrapers/outerbanks_web.py — Outer Banks NC STR page monitoring.

Outer Banks is one of the oldest and largest vacation rental markets in the US:
  - Multiple jurisdictions: Dare County, Currituck County, Kill Devil Hills,
    Nags Head, Kitty Hawk, Duck, Southern Shores, Manteo
  - Generally STR-friendly but increasing regulation
  - Nags Head: STR registration required ($25), $100 fine + $50/day if unregistered
  - Kill Devil Hills: Vacation rental permit through Planning & Inspections
  - Dare County: 6% occupancy tax on all rentals >14 days/year
  - NC Vacation Rental Act: written agreement required for all guests
  - NC state preemption limits some local restrictions (SB 291 pending 2025-26)
  - 6.75% state sales tax + 6% county occupancy tax = ~12.75% total

Data sources (verified March 2026):
  - Dare County occupancy tax: darenc.gov/departments/tax-department/occupancy-tax
  - Nags Head STR registration: nagsheadnc.gov/1013/Short-Term-Rentals
  - Kill Devil Hills planning: kdhnc.com/108/Planning-and-Inspections
"""

import logging
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)
CITY = "Outer Banks, NC"

WATCHED_PAGES = [
    {"name": "Dare County — Occupancy Tax", "url": "https://www.darenc.gov/departments/tax-department/occupancy-tax", "priority": "high"},
    {"name": "Nags Head — Short-Term Rentals", "url": "https://www.nagsheadnc.gov/1013/Short-Term-Rentals", "priority": "high"},
    {"name": "Kill Devil Hills — Planning & Inspections", "url": "https://www.kdhnc.com/108/Planning-and-Inspections", "priority": "medium"},
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
