"""
scrapers/lasvegas_web.py — Las Vegas NV STR page monitoring.

Las Vegas has a complex multi-jurisdiction STR framework:
  - City of Las Vegas: owner-occupied only, 660ft separation from other STRs,
    2,500ft from resort hotels, conditional use verification required
  - Clark County (unincorporated): AB363 mandated licensing, 1% cap per area,
    1,000ft separation, application period closed Aug 2023
  - Henderson, North Las Vegas: separate ordinances
  - NV Assembly Bill 363 (2021): statewide framework
  - $500K liability insurance required (City of LV)
  - Quiet hours 10pm-7am, outdoor amenities prohibited during quiet hours
  - One license per person/entity in Clark County
  - 2025: City of LV proposing ordinance amendments

Data sources:
  - City of LV STR: lasvegasnevada.gov/Business/Planning-Zoning/Code-Enforcement/Short-Term-Rentals
  - Clark County STR: clarkcountynv.gov/business/.../short_term_rentals/
  - Clark County FAQ: clarkcountynv.gov/business/.../frequently-asked-questions
"""

import logging
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)
CITY = "Las Vegas, NV"

WATCHED_PAGES = [
    {"name": "Las Vegas — Short-Term Rentals", "url": "https://www.lasvegasnevada.gov/Business/Planning-Zoning/Code-Enforcement/Short-Term-Rentals", "priority": "high"},
    {"name": "Clark County — STR Licensing", "url": "https://www.clarkcountynv.gov/business/doing_business_with_clark_county/divisions/regulated_business/short_term_rentals/", "priority": "high"},
    {"name": "Clark County — STR FAQ", "url": "https://www.clarkcountynv.gov/business/doing_business_with_clark_county/divisions/regulated_business/short_term_rentals/frequently-asked-questions", "priority": "medium"},
]

def run():
    log.info("=== Las Vegas page watcher starting ===")
    changes = 0
    for page in WATCHED_PAGES:
        try:
            if watch_page(page["name"], page["url"], CITY, page["priority"]):
                changes += 1
        except Exception as e:
            log.error("Error watching %s: %s", page["name"], e)
    log.info("Las Vegas page watcher done — checked: %d | changed: %d", len(WATCHED_PAGES), changes)
    return {"checked": len(WATCHED_PAGES), "changes": changes}

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print(run())
