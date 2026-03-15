"""
scrapers/savannah_web.py — Savannah GA STVR page monitoring.

Savannah has strict STVR regulations:
  - Limited to STVR Overlay District (Downtown, Victorian, Streetcar historic districts)
  - 20% cap of residential parcels per ward
  - $400 application fee, $250 annual renewal
  - Permits tracked via Deckard public portal
  - Certificate expires annually, must renew

Data sources:
  - Deckard public portal: str.deckard.com/ga-chatham-city_of_savannah/
  - STVR regulations: savannahga.gov/2327/STVR-Regulations
  - STVR application: savannahga.gov/2332/STVR-Application-Process
  - Public permit portal: savannahga.gov/2329/Short-Term-Rental-STR-Public-Portal
"""

import logging
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)

CITY = "Savannah, GA"

WATCHED_PAGES = [
    {
        "name": "Savannah — STVR Regulations",
        "url": "https://www.savannahga.gov/2327/STVR-Regulations",
        "priority": "high",
    },
    {
        "name": "Savannah — STVR Application Process",
        "url": "https://www.savannahga.gov/2332/STVR-Application-Process",
        "priority": "high",
    },
    {
        "name": "Savannah — STR Public Portal",
        "url": "https://www.savannahga.gov/2329/Short-Term-Rental-STR-Public-Portal",
        "priority": "medium",
    },
    {
        "name": "Savannah — Deckard STR Portal",
        "url": "https://str.deckard.com/ga-chatham-city_of_savannah/",
        "priority": "medium",
    },
]


def run():
    """Watch Savannah STVR regulation pages for changes."""
    log.info("=== Savannah page watcher starting ===")

    changes = 0
    for page in WATCHED_PAGES:
        try:
            changed = watch_page(
                name=page["name"],
                url=page["url"],
                city=CITY,
                priority=page["priority"],
            )
            if changed:
                changes += 1
        except Exception as e:
            log.error("Error watching %s: %s", page["name"], e)

    log.info("Savannah page watcher done — checked: %d | changed: %d",
             len(WATCHED_PAGES), changes)

    return {
        "checked": len(WATCHED_PAGES),
        "changes": changes,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    result = run()
    print(f"\nResult: {result}")
