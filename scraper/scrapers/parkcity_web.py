"""
scrapers/parkcity_web.py — Park City UT STR page monitoring.

Park City requires a Nightly Rental License for any stay <30 days.
Only allowed in designated zoning districts (resort areas, Old Town, Canyons Village).
Prohibited in residential zones like Prospector. Requires building inspection,
24/7 local contact, parking plan. Annual renewal. ~8% combined tax rate.
"""

import logging
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)
CITY = "Park City, UT"

WATCHED_PAGES = [
    {"name": "Park City — Nightly Rental License", "url": "https://parkcity.gov/departments/finance-accounting/apply-for-a-business-licenses/nightly-rental-license", "priority": "high"},
    {"name": "Park City — Business Licenses", "url": "https://parkcity.gov/departments/finance-accounting/apply-for-a-business-licenses", "priority": "medium"},
]

def run():
    log.info("=== Park City page watcher starting ===")
    changes = 0
    for page in WATCHED_PAGES:
        try:
            if watch_page(page["name"], page["url"], CITY, page["priority"]):
                changes += 1
        except Exception as e:
            log.error("Error watching %s: %s", page["name"], e)
    log.info("Park City page watcher done — checked: %d | changed: %d", len(WATCHED_PAGES), changes)
    return {"checked": len(WATCHED_PAGES), "changes": changes}

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print(run())
