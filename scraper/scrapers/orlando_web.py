"""
scrapers/orlando_web.py — Orlando FL STR page monitoring.

Orlando STR regulations (multi-jurisdictional):
  - City of Orlando: Home Sharing Registration required ($275 initial, $100 renewal)
  - Host must live on-site, be present, only one booking at a time
  - Max 50% of bedrooms can be rented
  - FL DBPR state license mandatory for all vacation rentals
  - Orange County: 6% Tourist Development Tax
  - State: 6% sales tax + 0.5% discretionary surtax
  - Combined tax burden: ~13% (state + county + city resort tax)
  - Annual permit renewal with interior inspection
  - Osceola County (Kissimmee): restricted to tourist zones

Data sources (verified March 2026):
  - City home sharing: orlando.gov/Initiatives/Home-Sharing-Registration
  - City planning: orlando.gov/Our-Government/Departments-Offices/Economic-Development/City-Planning
  - Orange County TDT: orangecountyfl.net/EconomicDevelopment
"""

import logging
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)
CITY = "Orlando, FL"

WATCHED_PAGES = [
    {"name": "Orlando — Home Sharing Registration", "url": "https://www.orlando.gov/Initiatives/Home-Sharing-Registration", "priority": "high"},
    {"name": "Orlando — City Planning STR", "url": "https://www.orlando.gov/Our-Government/Departments-Offices/Economic-Development/City-Planning", "priority": "medium"},
    {"name": "Orange County — Economic Development (TDT)", "url": "https://www.orangecountyfl.net/EconomicDevelopment/TouristDevelopmentTax.aspx", "priority": "medium"},
]

def run():
    log.info("=== Orlando page watcher starting ===")
    changes = 0
    for page in WATCHED_PAGES:
        try:
            if watch_page(page["name"], page["url"], CITY, page["priority"]):
                changes += 1
        except Exception as e:
            log.error("Error watching %s: %s", page["name"], e)
    log.info("Orlando page watcher done — checked: %d | changed: %d", len(WATCHED_PAGES), changes)
    return {"checked": len(WATCHED_PAGES), "changes": changes}

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print(run())
