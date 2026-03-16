"""
scrapers/nyc_web.py — New York City STR page monitoring.

NYC has effectively banned most STRs via Local Law 18 (2022):
  - Must register with Mayor's Office of Special Enforcement (OSE)
  - Host must be permanent occupant, present during stay
  - Max 2 guests, cannot rent entire unit
  - Booking platforms must verify registration before processing
  - ~60,000 illegal listings removed since enforcement began Sept 2023
  - ~3,000 registrations approved, 4,300+ denied
  - Rent-regulated and NYCHA units prohibited
  - $5,000 penalty per unregistered transaction
  - OSE actively filing lawsuits in 2025

Data sources:
  - OSE Registration: nyc.gov/site/specialenforcement/registration-law/registration.page
  - OSE Enforcement: nyc.gov/site/specialenforcement/registration-law/enforcement.page
  - Registration data: nyc.gov/site/specialenforcement/registration-law/registration-and-listing-data.page
  - Rules & laws: nyc.gov/site/specialenforcement/registration-law/registration-rules-and-laws.page
"""

import logging
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)
CITY = "New York City, NY"

WATCHED_PAGES = [
    {"name": "NYC — STR Registration (OSE)", "url": "https://www.nyc.gov/site/specialenforcement/registration-law/registration.page", "priority": "high"},
    {"name": "NYC — STR Enforcement", "url": "https://www.nyc.gov/site/specialenforcement/registration-law/enforcement.page", "priority": "high"},
    {"name": "NYC — Registration Data", "url": "https://www.nyc.gov/site/specialenforcement/registration-law/registration-and-listing-data.page", "priority": "medium"},
    {"name": "NYC — Registration Rules & Laws", "url": "https://www.nyc.gov/site/specialenforcement/registration-law/registration-rules-and-laws.page", "priority": "medium"},
]

def run():
    log.info("=== NYC page watcher starting ===")
    changes = 0
    for page in WATCHED_PAGES:
        try:
            if watch_page(page["name"], page["url"], CITY, page["priority"]):
                changes += 1
        except Exception as e:
            log.error("Error watching %s: %s", page["name"], e)
    log.info("NYC page watcher done — checked: %d | changed: %d", len(WATCHED_PAGES), changes)
    return {"checked": len(WATCHED_PAGES), "changes": changes}

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print(run())
