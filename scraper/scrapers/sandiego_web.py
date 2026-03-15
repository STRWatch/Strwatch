"""
scrapers/sandiego_web.py — San Diego STR page monitoring.

Watches the STRO regulation page and council docket pages for changes.

NOTE: San Diego's open data CSV (seshat.datasd.org) blocks datacenter IPs.
License-level tracking is deferred until we have a proxy or Vercel function.
For now, page watching catches regulation changes which is the highest-value signal.

San Diego has a 4-tier STRO license system with ~7,954 active licenses.
Tier 3 (whole-home) capped at 1% of housing stock. Tier 4 (Mission Beach) at 30%.
"""

import logging
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)

CITY = "San Diego, CA"

WATCHED_PAGES = [
    {
        "name": "San Diego — STRO Regulations",
        "url": "https://www.sandiego.gov/treasurer/short-term-residential-occupancy",
        "priority": "high",
    },
    {
        "name": "San Diego — STRO FAQ & Updates",
        "url": "https://www.sandiego.gov/treasurer/short-term-residential-occupancy/faqs",
        "priority": "medium",
    },
    {
        "name": "San Diego — City Council Dockets",
        "url": "https://www.sandiego.gov/city-clerk/officialdocs/legisdocs",
        "priority": "medium",
    },
]


def run():
    """Watch San Diego STRO regulation pages for changes."""
    log.info("=== San Diego page watcher starting ===")

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

    log.info("San Diego page watcher done — checked: %d | changed: %d",
             len(WATCHED_PAGES), changes)

    return {
        "checked": len(WATCHED_PAGES),
        "changes": changes,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    result = run()
    print(f"\nResult: {result}")
