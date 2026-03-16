"""
scrapers/la_web.py — Los Angeles STR page monitoring.

LA Home-Sharing Ordinance (adopted Dec 2018, enforced Nov 2019):
  - Primary residence only (6+ months/year)
  - 120-day annual cap (extended home-sharing requires $850+ approval)
  - $89 annual registration fee
  - RSO (Rent Stabilization Ordinance) units prohibited
  - Registration number required on all listings
  - 2 verified citations = immediate revocation + 1 year ban
  - 24/7 complaint hotline: (213) 267-7788
  - Platforms required to verify registration numbers
  - No more than 8 people outdoors after 10pm

Data sources:
  - Planning home-sharing: planning.lacity.gov/project-review/home-sharing
  - Home-sharing FAQ: planning.lacity.gov/blog/what-home-sharing-program
  - LAHD ordinance info: housing.lacity.gov/articles/home-sharing-ordinance
"""

import logging
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)
CITY = "Los Angeles, CA"

WATCHED_PAGES = [
    {"name": "LA — Home-Sharing Program", "url": "https://planning.lacity.gov/project-review/home-sharing", "priority": "high"},
    {"name": "LA — Home-Sharing FAQ", "url": "https://planning.lacity.gov/blog/what-home-sharing-program", "priority": "high"},
    {"name": "LA — Housing Dept STR Info", "url": "https://housing.lacity.gov/articles/home-sharing-ordinance", "priority": "medium"},
]

def run():
    log.info("=== Los Angeles page watcher starting ===")
    changes = 0
    for page in WATCHED_PAGES:
        try:
            if watch_page(page["name"], page["url"], CITY, page["priority"]):
                changes += 1
        except Exception as e:
            log.error("Error watching %s: %s", page["name"], e)
    log.info("LA page watcher done — checked: %d | changed: %d", len(WATCHED_PAGES), changes)
    return {"checked": len(WATCHED_PAGES), "changes": changes}

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print(run())
