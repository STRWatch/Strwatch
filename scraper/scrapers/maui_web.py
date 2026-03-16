"""
scrapers/maui_web.py — Maui County HI STR page monitoring.

Maui has undergone massive STR regulatory upheaval:
  - Moratorium on new STR permits in many areas
  - Bill 41 / Ordinance 5831: phaseout of STRs in apartment districts
  - Short-Term Rental Home (STRH) permits: limited, application complex
  - B&B permits: owner-occupied, max 6 bedrooms
  - Transient Vacation Rental (TVR): only in resort zones
  - Maui County Real Property Tax: STR classification = highest rate
  - GET 4.5% + TAT 10.25% + Maui surcharge 3% = ~17.75% total tax
  - Post-wildfire housing crisis accelerated enforcement
  - Active community opposition to STRs

Data sources:
  - County STRH info: mauicounty.gov/2553/Short-Term-Rental-Homes-STRH
  - County planning: mauicounty.gov/121/Current-Division
  - County council: mauicounty.us (legislation tracking)
"""

import logging
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)
CITY = "Maui, HI"

WATCHED_PAGES = [
    {"name": "Maui County — STRH Permits", "url": "https://www.mauicounty.gov/2553/Short-Term-Rental-Homes-STRH", "priority": "high"},
    {"name": "Maui County — Planning Current Division", "url": "https://www.mauicounty.gov/121/Current-Division", "priority": "medium"},
    {"name": "Maui County — B&B Permits", "url": "https://www.mauicounty.gov/1098/Bed-Breakfast-BB-Permits", "priority": "medium"},
]

def run():
    log.info("=== Maui page watcher starting ===")
    changes = 0
    for page in WATCHED_PAGES:
        try:
            if watch_page(page["name"], page["url"], CITY, page["priority"]):
                changes += 1
        except Exception as e:
            log.error("Error watching %s: %s", page["name"], e)
    log.info("Maui page watcher done — checked: %d | changed: %d", len(WATCHED_PAGES), changes)
    return {"checked": len(WATCHED_PAGES), "changes": changes}

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print(run())
