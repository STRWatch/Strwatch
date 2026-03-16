"""
scrapers/tybee_web.py — Tybee Island GA STR page monitoring.

Tybee Island (separate jurisdiction from Savannah):
  - ~1,100 STVR permit cap (roughly 40% of all housing)
  - Lottery system when permits become available
  - Annual STVR certificate required: $400 application + $250 renewal
  - Must use licensed management company or be self-managing with local contact
  - Occupancy: 2 per bedroom + 4 additional, max varies by zone
  - Quiet hours 10pm-8am
  - 8% combined lodging tax (state + county + city)
  - Parking: 1 space per bedroom
  - Active enforcement with complaint hotline
  - Separate from Savannah proper (different rules entirely)

Data sources:
  - City STVR: cityoftybee.org/page/short-term-vacation-rental-information
  - City code/permits: cityoftybee.org/page/permits-licensing
  - Chatham County tax: chathamcountyga.gov
"""

import logging
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)
CITY = "Tybee Island, GA"

WATCHED_PAGES = [
    {"name": "Tybee Island — STVR Information", "url": "https://www.cityoftybee.org/page/short-term-vacation-rental-information", "priority": "high"},
    {"name": "Tybee Island — Permits & Licensing", "url": "https://www.cityoftybee.org/page/permits-licensing", "priority": "medium"},
    {"name": "Tybee Island — City Council Agendas", "url": "https://www.cityoftybee.org/page/agendas-minutes", "priority": "medium"},
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
