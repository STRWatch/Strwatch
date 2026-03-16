"""
scrapers/destin_web.py — Destin FL / 30A / Walton County STR page monitoring.

Destin & 30A is one of the top beach STR markets in the US:
  - Multiple jurisdictions: City of Destin, Walton County (30A), Okaloosa County
  - FL DBPR state license required for all vacation rentals
  - Destin: Business Tax Receipt required, vacation rental registration
  - Walton County: Tourist Development Tax 5%, active enforcement
  - Okaloosa County: Tourist Development Tax 5%
  - State sales tax 6% + county TDT = 11-12% total
  - Occupancy limits, noise ordinances, parking requirements
  - High investor density — significant property management industry
  - Hurricane evacuation compliance requirements

Data sources:
  - City of Destin: cityofdestin.com/150/Short-Term-Vacation-Rentals
  - Walton County TDC: visitsouthwalton.com (tourism development council)
  - Okaloosa County tax collector: okaloosatax.com
"""

import logging
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)
CITY = "Destin/30A, FL"

WATCHED_PAGES = [
    {"name": "Destin — Short-Term Vacation Rentals", "url": "https://www.cityofdestin.com/150/Short-Term-Vacation-Rentals", "priority": "high"},
    {"name": "Destin — Code Compliance", "url": "https://www.cityofdestin.com/151/Code-Compliance", "priority": "medium"},
    {"name": "Walton County — Tourist Dev Tax", "url": "https://waltoncountytdc.com/tourist-development-tax/", "priority": "medium"},
]

def run():
    log.info("=== Destin/30A page watcher starting ===")
    changes = 0
    for page in WATCHED_PAGES:
        try:
            if watch_page(page["name"], page["url"], CITY, page["priority"]):
                changes += 1
        except Exception as e:
            log.error("Error watching %s: %s", page["name"], e)
    log.info("Destin/30A page watcher done — checked: %d | changed: %d", len(WATCHED_PAGES), changes)
    return {"checked": len(WATCHED_PAGES), "changes": changes}

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print(run())
