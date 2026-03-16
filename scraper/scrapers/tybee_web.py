"""
scrapers/tybee_web.py — Tybee Island GA STR page monitoring.

Tybee Island (separate jurisdiction from Savannah):
  - STR certificates valid Jan 1 - Dec 31, must renew annually
  - Renewal window: Jan 1 - March 31 each year
  - No new certificates in R-1, R-1B, or R-2 zoning districts
  - 7% local occupational room tax due monthly by 20th
  - Occupational Tax Certificate (OTC) also required (some exemptions)
  - Must designate local agent available at all times, respond within 1 hour
  - Liability insurance required, must inform insurer of STVR use
  - Dedicated STVR Coordinator on staff since 2023
  - 24/7 complaint hotline: (912) 325-7469

Data sources (verified March 2026):
  - STR page: cityoftybee.org/466/Short-Term-Rentals
  - STR FAQ: cityoftybee.org/faq.aspx?TID=29
  - STR ordinance: via municode library
"""

import logging
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)
CITY = "Tybee Island, GA"

WATCHED_PAGES = [
    {"name": "Tybee Island — Short-Term Rentals", "url": "https://www.cityoftybee.org/466/Short-Term-Rentals", "priority": "high"},
    {"name": "Tybee Island — STR FAQ", "url": "https://www.cityoftybee.org/faq.aspx?TID=29", "priority": "high"},
    {"name": "Tybee Island — STR Ordinance Alert", "url": "https://www.cityoftybee.org/CivicAlerts.aspx?AID=681&ARC=1203", "priority": "medium"},
]

def run():
    log.info("=== Tybee Island page watcher starting ===")
    changes = 0
    for page in WATCHED_PAGES:
        try:
            if watch_page(page["name"], page["url"], CITY, page["priority"]):
                changes += 1
        except Exception as e:
            log.error("Error watching %s: %s", page["name"], e)
    log.info("Tybee Island page watcher done — checked: %d | changed: %d", len(WATCHED_PAGES), changes)
    return {"checked": len(WATCHED_PAGES), "changes": changes}

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print(run())
