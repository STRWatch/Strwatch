"""
scrapers/indianapolis_web.py — Indianapolis STR page monitoring + council proposal scanning.

Indianapolis does NOT use the Legistar public API (slug exists but is unconfigured).
Instead we:
  1. Hash-watch indy.gov STR pages and DBNS permit pages
  2. Hash-watch the Municode Meetings portal (indianapolis-in.municodemeetings.com)
  3. Hash-watch the City-County Council Proposals page on indy.gov
  4. Hash-watch the Department of Metropolitan Development (DMD) meetings page

Key context:
  - STR permit program launched January 1, 2025 under DBNS
  - $150 permit fee, annual renewal (free), non-transferable
  - Marion County 10% innkeeper's tax + 7% Indiana state sales tax = 17% total
  - 3 violations in 12 months → permit revocation up to 1 year
  - Indiana HB 1035 prevents outright STR bans, allows regulation
  - Proposals page and DMD are highest-value sources for zoning/STR changes
"""

import logging
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)

INDIANAPOLIS_PAGES = [
    # ── Core STR pages ──
    {
        "name": "Indianapolis — STR Registration",
        "url": "https://www.indy.gov/activity/short-term-rental-registration",
        "city": "Indianapolis",
        "priority": "high",
    },
    {
        "name": "Indianapolis — DBNS Permits & Licensing",
        "url": "https://www.indy.gov/agency/department-of-business-and-neighborhood-services",
        "city": "Indianapolis",
        "priority": "medium",
    },
    {
        "name": "Indianapolis — Marion County Innkeeper's Tax",
        "url": "https://www.indy.gov/activity/innkeepers-tax",
        "city": "Indianapolis",
        "priority": "medium",
    },
    # ── Legislation & proposals ──
    {
        "name": "Indianapolis — City-County Council Proposals",
        "url": "https://www.indy.gov/activity/city-county-council-proposals",
        "city": "Indianapolis",
        "priority": "high",
    },
    {
        "name": "Indianapolis — Council Meeting Agendas",
        "url": "https://www.indy.gov/activity/council-meeting-agendas",
        "city": "Indianapolis",
        "priority": "high",
    },
    {
        "name": "Indianapolis — Municode Meetings Portal",
        "url": "https://indianapolis-in.municodemeetings.com/",
        "city": "Indianapolis",
        "priority": "medium",
    },
    {
        "name": "Indianapolis — DMD Meetings (zoning/planning)",
        "url": "https://indianapolis-in.municodemeetings.com/DMDmeetings",
        "city": "Indianapolis",
        "priority": "high",
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
