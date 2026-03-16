"""
scrapers/hawaii_web.py — Honolulu + Maui HI STR page monitoring.

Hawaii has extremely strict STR regulations:
  - Honolulu (Oahu): 90-day minimum in residential zones, STRs only in resort areas
  - Bill 41 (2022): created registration system, $500 fine/day for violations
  - Maui County: moratorium on new STR permits in many areas
  - Both require state GET (4.5%) + TAT (10.25%) + county surcharge
  - Aggressive enforcement with dedicated staff and third-party monitoring
  - Platforms required to verify permit numbers
"""

import logging
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)
CITY = "Honolulu, HI"

WATCHED_PAGES = [
    {"name": "Honolulu — Short-Term Rentals", "url": "https://www.honolulu.gov/dpp-str", "priority": "high"},
    {"name": "Honolulu — DPP STR Registration", "url": "https://www.honolulu.gov/dpp/short-term-rental-registration.html", "priority": "high"},
    {"name": "Maui County — Short-Term Rental Info", "url": "https://www.mauicounty.gov/2553/Short-Term-Rental-Homes-STRH", "priority": "high"},
]

def run():
    log.info("=== Hawaii page watcher starting ===")
    changes = 0
    for page in WATCHED_PAGES:
        try:
            if watch_page(page["name"], page["url"], CITY, page["priority"]):
                changes += 1
        except Exception as e:
            log.error("Error watching %s: %s", page["name"], e)
    log.info("Hawaii page watcher done — checked: %d | changed: %d", len(WATCHED_PAGES), changes)
    return {"checked": len(WATCHED_PAGES), "changes": changes}

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print(run())
