"""
scrapers/orlando_web.py — Orlando / Orange County STR page monitoring.

Watches:
1. orlando.gov Home Sharing Registration page
2. orlando.gov City Planning page
3. Orange County Comptroller TDT page (occompt.com — actual tax authority)
"""

import logging
import config
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)

PAGES = [
    {
        "name": "Orlando — Home Sharing Registration",
        "url": "https://www.orlando.gov/Initiatives/Home-Sharing-Registration",
        "city": "Orlando",
        "priority": "high",
    },
    {
        "name": "Orlando — City Planning",
        "url": "https://www.orlando.gov/Our-Government/Departments-Offices/Executive-Offices/CAO/City-Planning",
        "city": "Orlando",
        "priority": "medium",
    },
    {
        "name": "Orange County — Tourist Development Tax (Comptroller)",
        "url": "https://www.occompt.com/270/Tourist-Development-Tax",
        "city": "Orlando",
        "priority": "high",
    },
]


def run():
    log.info("=== Orlando page watcher starting ===")
    changes = 0
    for page in PAGES:
        try:
            changed = watch_page(
                name=page["name"],
                url=page["url"],
                city=page["city"],
                priority=page["priority"],
            )
            if changed:
                changes += 1
        except Exception as e:
            log.error("Error watching %s: %s", page["name"], e)

    log.info("Orlando page watcher done — checked: %d | changed: %d", len(PAGES), changes)
    return {"checked": len(PAGES), "changes": changes}


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    result = run()
    print(f"\nResult: {result}")
