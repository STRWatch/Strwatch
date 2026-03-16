"""
scrapers/breckenridge_web.py — Breckenridge CO + Summit County STR page monitoring.

Breckenridge has 4 STR zones with caps and waitlists:
  - Resort Zone: 1,816 licenses (unlimited effective)
  - Zone 1 Tourism: 1,680 allowed (1,220 issued)
  - Zone 2 Downtown Core: 130 allowed (waitlist active)
  - Zone 3 Single Family: 390 allowed (waitlist 160+)
  - $250 annual license fee, expires May 31 each year
  - Responsible Agent required (60-min response time, 24/7)
  - Parking: 1 space/bedroom + 1 additional
  - Summit County: Type I (locals) and Type II (STR) licenses, basin caps
"""

import logging
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)
CITY = "Breckenridge, CO"

WATCHED_PAGES = [
    {"name": "Breckenridge — STR Licensing", "url": "https://www.townofbreckenridge.com/government/departments/community-development/short-term-rentals", "priority": "high"},
    {"name": "Summit County — STR Regulations", "url": "https://www.summitcountyco.gov/services/community_development/short_term_rentals/str_regulations.php", "priority": "high"},
    {"name": "Summit County — STR License Application", "url": "https://www.summitcountyco.gov/services/community_development/short_term_rentals/license_applications.php", "priority": "medium"},
]

def run():
    log.info("=== Breckenridge page watcher starting ===")
    changes = 0
    for page in WATCHED_PAGES:
        try:
            if watch_page(page["name"], page["url"], CITY, page["priority"]):
                changes += 1
        except Exception as e:
            log.error("Error watching %s: %s", page["name"], e)
    log.info("Breckenridge page watcher done — checked: %d | changed: %d", len(WATCHED_PAGES), changes)
    return {"checked": len(WATCHED_PAGES), "changes": changes}

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print(run())
