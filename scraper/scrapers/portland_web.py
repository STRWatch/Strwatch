"""
scrapers/portland_web.py — Portland OR STR page monitoring.

Portland Accessory Short-Term Rental (ASTR) regulations:
  - Type A: 1-2 bedrooms, max 5 guests, $360/2yr permit
  - Type B: 3-5 bedrooms, conditional use review, ~$9,000
  - Resident must occupy 270+ days/year
  - Max 95 nights absent while renting
  - Transient Lodging Tax: 11.5% (city 6% + county 5.5%)
  - Portland Ombudsman found fines 27x higher than comparable cities (2026)
  - ADUs cannot be used as STRs unless owner-occupied
  - Permit number required on all listings

Data sources (verified March 2026):
  - ASTR permits main: portland.gov/bds/astr-permits
  - ASTR before you apply: portland.gov/bds/astr-permits/before-you-apply
  - ASTR maintaining permits: portland.gov/bds/astr-permits/maintain-astr-permits
"""

import logging
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)
CITY = "Portland, OR"

WATCHED_PAGES = [
    {"name": "Portland — ASTR Permits", "url": "https://www.portland.gov/bds/astr-permits", "priority": "high"},
    {"name": "Portland — ASTR Before You Apply", "url": "https://www.portland.gov/bds/astr-permits/before-you-apply", "priority": "high"},
    {"name": "Portland — Maintaining ASTR Permits", "url": "https://www.portland.gov/bds/astr-permits/maintain-astr-permits", "priority": "medium"},
]

def run():
    log.info("=== Portland page watcher starting ===")
    changes = 0
    for page in WATCHED_PAGES:
        try:
            if watch_page(page["name"], page["url"], CITY, page["priority"]):
                changes += 1
        except Exception as e:
            log.error("Error watching %s: %s", page["name"], e)
    log.info("Portland page watcher done — checked: %d | changed: %d", len(WATCHED_PAGES), changes)
    return {"checked": len(WATCHED_PAGES), "changes": changes}

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print(run())
