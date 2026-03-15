"""
scrapers/sf_web.py — San Francisco STR page monitoring + open data.

SF has among the strictest STR regulations in the US:
  - Must be permanent resident (275+ nights/year)
  - 90-night cap on un-hosted stays per calendar year
  - $925 application fee (non-refundable), 2-year certificate
  - 14% Transient Occupancy Tax
  - Quarterly reporting required
  - Max 5 simultaneous bookings

Data sources:
  - OSTR pages: sfplanning.org/office-short-term-rentals
  - SF Business Portal: businessportal.sfgov.org
  - SF Open Data (SODA): data.sfgov.org (311 complaints include STR category)
  - OSTR Verification API: api.sfgov.org (requires app key — future enhancement)
"""

import logging
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)

CITY = "San Francisco, CA"

WATCHED_PAGES = [
    {
        "name": "SF — Office of Short-Term Rentals",
        "url": "https://sfplanning.org/office-short-term-rentals",
        "priority": "high",
    },
    {
        "name": "SF — STR Compliance & Quarterly Reporting",
        "url": "https://sfplanning.org/str/maintain-your-certified-host-status",
        "priority": "high",
    },
    {
        "name": "SF — STR FAQs",
        "url": "https://sfplanning.org/str/faqs-short-term-rentals",
        "priority": "medium",
    },
    {
        "name": "SF — Guide to Opening STR",
        "url": "https://www.sf.gov/guide-opening-short-term-residential-rental",
        "priority": "medium",
    },
]


def run():
    """Watch San Francisco STR regulation pages for changes."""
    log.info("=== San Francisco page watcher starting ===")

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

    log.info("SF page watcher done — checked: %d | changed: %d",
             len(WATCHED_PAGES), changes)

    return {
        "checked": len(WATCHED_PAGES),
        "changes": changes,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    result = run()
    print(f"\nResult: {result}")
