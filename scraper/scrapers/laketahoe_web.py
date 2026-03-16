"""
scrapers/laketahoe_web.py — Lake Tahoe STR page monitoring.

Watches:
1. South Lake Tahoe — Short-Term Rentals main page
2. South Lake Tahoe — Measure T FAQ page (court struck down March 2025, new VHR rules)
3. Placer County — STR info page (North Lake Tahoe side)
"""

import logging
import config
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)

PAGES = [
    {
        "name": "South Lake Tahoe — Short-Term Rentals",
        "url": "https://www.cityofslt.us/2431/Short-Term-Rentals",
        "city": "Lake Tahoe",
        "priority": "high",
    },
    {
        "name": "South Lake Tahoe — Measure T FAQ",
        "url": "https://www.cityofslt.us/Faq.aspx?QID=258",
        "city": "Lake Tahoe",
        "priority": "high",
    },
    {
        "name": "Placer County — Short-Term Rentals",
        "url": "https://www.placer.ca.gov/3065/Short-Term-Rentals",
        "city": "Lake Tahoe",
        "priority": "medium",
    },
]


def run():
    log.info("=== Lake Tahoe page watcher starting ===")
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

    log.info("Lake Tahoe page watcher done — checked: %d | changed: %d", len(PAGES), changes)
    return {"checked": len(PAGES), "changes": changes}


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    result = run()
    print(f"\nResult: {result}")
