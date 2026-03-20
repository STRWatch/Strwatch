"""
scrapers/indianapolis_web.py — Indianapolis STR page monitoring.

Indianapolis STR permit program launched January 1, 2025.
Administered by Department of Business & Neighborhood Services (DBNS).
Key facts:
  - $150 permit fee, annual renewal (free), non-transferable
  - 17% total tax: 7% state sales tax + 10% Marion County innkeeper's tax
  - 3 violations in 12 months = permit revocation up to 1 year
  - State law (HB 1035) prevents outright bans but allows regulation
  - City actively soliciting neighbor reports on unregistered STRs

Pages watched:
  1. indy.gov STR main page
  2. DBNS licensing/permit page
  3. Marion County innkeeper's tax page
  4. Indianapolis City-County Council agenda index
"""

import logging
from datetime import date

import config
from scrapers.austin_web import watch_page  # Reuse shared hash-diff watcher

log = logging.getLogger(__name__)

# Indianapolis-specific pages to monitor
INDIANAPOLIS_PAGES = [
    {
        "name": "Indianapolis STR Main Page",
        "url": "https://www.indy.gov/activity/short-term-rental-registration",
        "city": "Indianapolis",
        "priority": "high",
    },
    {
        "name": "Indianapolis DBNS Permits & Licensing",
        "url": "https://www.indy.gov/agency/department-of-business-and-neighborhood-services",
        "city": "Indianapolis",
        "priority": "medium",
    },
    {
        "name": "Marion County Innkeeper's Tax",
        "url": "https://www.indy.gov/activity/innkeepers-tax",
        "city": "Indianapolis",
        "priority": "medium",
    },
    {
        "name": "Indianapolis City-County Council Agendas",
        "url": "https://council.indy.gov/meeting-documents",
        "city": "Indianapolis",
        "priority": "high",
    },
    {
        "name": "Indianapolis STR Accela Portal",
        "url": "https://mylicense.indy.gov/EpisealV2/default.aspx",
        "city": "Indianapolis",
        "priority": "low",
    },
]


def run():
    """Watch all Indianapolis STR-related pages for changes."""
    log.info("=== Indianapolis page watcher starting (%d pages) ===", len(INDIANAPOLIS_PAGES))

    changes = 0
    errors = 0

    for page in INDIANAPOLIS_PAGES:
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
            errors += 1
            log.error("Error watching %s: %s", page["name"], e)

    log.info(
        "Indianapolis page watcher done — checked: %d | changed: %d | errors: %d",
        len(INDIANAPOLIS_PAGES), changes, errors,
    )

    return {
        "checked": len(INDIANAPOLIS_PAGES),
        "changes": changes,
        "errors": errors,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    result = run()
    print(f"\nResult: {result}")
