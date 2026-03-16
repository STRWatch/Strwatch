"""
scrapers/boston_web.py — Boston MA STR page monitoring.

Boston STR Ordinance (effective Jan 1, 2019):
  - Three-tiered system: Limited Share ($25/yr), Home Share ($100/yr), Owner-Adjacent
  - Must be operator's primary residence (9+ months/year)
  - Limited Share: max 3 bedrooms/6 guests, host present
  - Home Share: max 5 bedrooms/10 guests, whole unit
  - Owner-Adjacent: must be in same 2-3 unit building owner lives in
  - RSO, income-restricted, and "Problem Property" units prohibited
  - 3+ violations in 6 months = ineligible
  - Must notify abutters within 30 days of registration
  - Platforms must provide monthly data to city
  - Registration number required on all listings
  - Open data: Short-Term Rental Eligibility Dataset refreshed nightly

Data sources:
  - ISD STR page: boston.gov/departments/inspectional-services/short-term-rentals
  - Permitting portal: permits.boston.gov/departments/inspectional-services/short-term-rentals
  - STR eligibility data: data.boston.gov/dataset/short-term-rental-eligibility
"""

import logging
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)
CITY = "Boston, MA"

WATCHED_PAGES = [
    {"name": "Boston — Short-Term Rentals (ISD)", "url": "https://www.boston.gov/departments/inspectional-services/short-term-rentals", "priority": "high"},
    {"name": "Boston — STR Permitting Portal", "url": "https://permits.boston.gov/departments/inspectional-services/short-term-rentals", "priority": "high"},
    {"name": "Boston — STR Eligibility Data", "url": "https://data.boston.gov/dataset/short-term-rental-eligibility", "priority": "medium"},
]

def run():
    log.info("=== Boston page watcher starting ===")
    changes = 0
    for page in WATCHED_PAGES:
        try:
            if watch_page(page["name"], page["url"], CITY, page["priority"]):
                changes += 1
        except Exception as e:
            log.error("Error watching %s: %s", page["name"], e)
    log.info("Boston page watcher done — checked: %d | changed: %d", len(WATCHED_PAGES), changes)
    return {"checked": len(WATCHED_PAGES), "changes": changes}

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print(run())
