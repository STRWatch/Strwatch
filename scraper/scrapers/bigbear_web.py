"""
scrapers/bigbear_web.py — Big Bear CA STR page monitoring.

Big Bear Lake has strict vacation rental regulations:
  - Vacation Home Rental (VHR) permit required
  - Annual inspection and fire safety compliance
  - Occupancy limits based on bedrooms and septic/sewer capacity
  - Parking requirements: 1 space per bedroom
  - Noise ordinances strictly enforced (bear country)
  - Two jurisdictions: City of Big Bear Lake vs San Bernardino County
"""

import logging
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)
CITY = "Big Bear, CA"

WATCHED_PAGES = [
    {"name": "Big Bear Lake — Vacation Home Rentals", "url": "https://www.citybigbearlake.com/visitors/vacation-home-rentals", "priority": "high"},
    {"name": "Big Bear Lake — Code Enforcement", "url": "https://www.citybigbearlake.com/city-hall/code-enforcement", "priority": "medium"},
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
