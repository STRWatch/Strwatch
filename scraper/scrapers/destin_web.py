"""
scrapers/destin_web.py — Destin FL / 30A / Walton County STR page monitoring.

Destin STR regulations:
  - $200 registration fee per unit (single family, townhome, duplex, triplex)
  - Late fees: $100 after March 31, $500 after June 1
  - Max overnight occupancy: 2 adults/bedroom + 4 additional, cap 24
  - Quiet hours 10pm-7am
  - Sign required on property within 7 days of registration
  - Local responsible party within 1 hour required
  - FL DBPR state license mandatory
  - Walton County (30A): separate Tourist Development Tax 5%
  - Registration renews annually starting January 1

Data sources (verified March 2026):
  - Code Compliance: cityofdestin.com/90/Code-Compliance
  - STR FAQ: cityofdestin.com/faq.aspx?TID=19
  - Resources: cityofdestin.com/200/Useful-Resources-Links
  - Walton County TDC: waltoncountytdc.com
"""

import logging
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)
CITY = "Destin/30A, FL"

WATCHED_PAGES = [
    {"name": "Destin — Code Compliance", "url": "https://www.cityofdestin.com/90/Code-Compliance", "priority": "high"},
    {"name": "Destin — STR FAQ", "url": "https://www.cityofdestin.com/faq.aspx?TID=19", "priority": "high"},
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
