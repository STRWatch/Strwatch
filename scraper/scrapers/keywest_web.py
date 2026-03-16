"""
scrapers/keywest_web.py — Key West FL STR page monitoring.

Key West has perhaps the most exclusive STR market in the US:
  - Finite supply of transient licenses — no new ones issued
  - Licenses trade on secondary market for $400K-$500K+
  - Two tiers: transient (<28 days) and non-transient (monthly)
  - Truman Annex transient licenses expired Dec 2025
  - FL DBPR license + City BTR + Monroe County BTR required
  - Fire and Life Safety inspection for initial + renewal
  - 12.5% total tax rate (6% state + 4% county TDT + 2.5% local)
  - Average STR revenue ~$118K/year
  - 24/7 contact required, license medallion displayed on property

Data sources:
  - City licensing FAQ: cityofkeywest-fl.gov
  - Transient rental map: cityofkeywest-fl.gov/856/
  - Monroe County STR info: monroecounty-fl.gov
"""

import logging
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)

CITY = "Key West, FL"

WATCHED_PAGES = [
    {
        "name": "Key West — Residential Rental Requirements FAQ",
        "url": "https://www.cityofkeywest-fl.gov/FAQ.aspx?QID=192",
        "priority": "high",
    },
    {
        "name": "Key West — License Caps FAQ",
        "url": "https://www.cityofkeywest-fl.gov/Faq.aspx?QID=193",
        "priority": "high",
    },
    {
        "name": "Key West — Transient Rental Property Map",
        "url": "https://www.cityofkeywest-fl.gov/856/Map-Addresses-of-Transient-Rental-Proper",
        "priority": "medium",
    },
]


def run():
    """Watch Key West STR regulation pages for changes."""
    log.info("=== Key West page watcher starting ===")

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

    log.info("Key West page watcher done — checked: %d | changed: %d",
             len(WATCHED_PAGES), changes)

    return {
        "checked": len(WATCHED_PAGES),
        "changes": changes,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    result = run()
    print(f"\nResult: {result}")
