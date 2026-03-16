"""
scrapers/bigbear_web.py — Big Bear CA STR page monitoring.

Big Bear Lake has strict vacation rental regulations:
  - Vacation Rental Program registration required (not called "VHR" anymore)
  - Annual inspection and fire safety compliance
  - Owner and Agent certification exam (25 questions, 100% pass)
  - Vacation Rental Ordinance 2023-518 is current ordinance
  - $5,000 fine for operating without license
  - $2,500 fine for advertising without permit number
  - TOT: 10% (increased Jan 2025 via Measure P) + 3% TBID
  - Annual license renewal with 60-day warning system
  - Off-street paved parking required by 2026
  - Two jurisdictions: City of Big Bear Lake (92315) vs San Bernardino County

Data sources (verified March 2026):
  - VR Program: citybigbearlake.com/index.php/en/departments/city-manager/transient-private-home-rental-tphr-program
  - VR 101 newsletter: citybigbearlake.com/index.php/en/vacation-rental-101
  - VRO Review: citybigbearlake.com/index.php/en/vro-review
"""

import logging
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)
CITY = "Big Bear, CA"

WATCHED_PAGES = [
    {"name": "Big Bear Lake — Vacation Rental Program", "url": "https://citybigbearlake.com/index.php/en/departments/city-manager/transient-private-home-rental-tphr-program", "priority": "high"},
    {"name": "Big Bear Lake — Vacation Rental 101", "url": "https://www.citybigbearlake.com/index.php/en/vacation-rental-101", "priority": "high"},
    {"name": "Big Bear Lake — VRO Review & Ordinance", "url": "https://www.citybigbearlake.com/index.php/en/vro-review", "priority": "medium"},
]

def run():
    log.info("=== Big Bear page watcher starting ===")
    changes = 0
    for page in WATCHED_PAGES:
        try:
            if watch_page(page["name"], page["url"], CITY, page["priority"]):
                changes += 1
        except Exception as e:
            log.error("Error watching %s: %s", page["name"], e)
    log.info("Big Bear page watcher done — checked: %d | changed: %d", len(WATCHED_PAGES), changes)
    return {"checked": len(WATCHED_PAGES), "changes": changes}

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print(run())
