"""
scrapers/portland_web.py — Portland OR STR page monitoring.

Portland STR regulations:
  - Permit required: Type A (accessory, host present) or Type B (primary residence, host absent)
  - Must be operator's primary residence
  - Type B limited to 95 nights/year when host is absent
  - $190 permit fee (2-year), BDS safety inspection required
  - Transient Lodging Tax: 11.5% (city 6% + county 5.5%)
  - Must display permit number on all listings
  - Oregon preemption debate ongoing — SB 1554 (2024) proposed limits on local bans
  - Accessory Dwelling Units (ADUs) cannot be used as STRs unless owner-occupied
  - Noise, parking, trash rules enforced via complaint system

Data sources:
  - BDS STR permits: portland.gov/bds/short-term-rentals
  - Revenue Division lodging tax: portland.gov/revenue/transient-lodging-tax
  - City code: portland.gov/code/33/207
"""

import logging
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)
CITY = "Portland, OR"

WATCHED_PAGES = [
    {"name": "Portland — STR Permits (BDS)", "url": "https://www.portland.gov/bds/short-term-rentals", "priority": "high"},
    {"name": "Portland — Transient Lodging Tax", "url": "https://www.portland.gov/revenue/transient-lodging-tax", "priority": "medium"},
    {"name": "Portland — STR Code (33.207)", "url": "https://www.portland.gov/code/33/207", "priority": "medium"},
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
