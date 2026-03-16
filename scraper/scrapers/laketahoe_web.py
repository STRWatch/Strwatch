"""
scrapers/laketahoe_web.py — Lake Tahoe CA/NV STR page monitoring.

Lake Tahoe spans multiple jurisdictions with complex STR rules:
  - South Lake Tahoe: Measure T struck down March 2025, moratorium in
    residential areas while new ordinance drafted. $535 VHR permit fee.
    Bear box required. Permits handled by Police Department.
  - El Dorado County: VHR permits with neighborhood caps
  - Placer County (North Shore): STR permit, $1,000/day fines
  - TRPA (Tahoe Regional Planning Agency): environmental overlays
  - TOT rates vary: 10-14% depending on jurisdiction
  - Massive regulatory upheaval — Measure T reversal in 2025 opened
    residential areas to VHRs again after years of prohibition

Data sources (verified March 2026):
  - SLT Short-Term Rentals: cityofslt.us/2431/Short-Term-Rentals
  - SLT Measure T: cityofslt.us/2418/Measure-T-updated-642025
  - El Dorado County VHR: edcgov.us/Government/Planning/vacation-home-rentals
  - Placer County STR: placer.ca.gov/str
"""

import logging
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)
CITY = "Lake Tahoe, CA"

WATCHED_PAGES = [
    {"name": "South Lake Tahoe — Short-Term Rentals", "url": "https://www.cityofslt.us/2431/Short-Term-Rentals", "priority": "high"},
    {"name": "South Lake Tahoe — Measure T Updates", "url": "https://cityofslt.us/2418/Measure-T-updated-642025", "priority": "high"},
    {"name": "Placer County — STR Info", "url": "https://www.placer.ca.gov/str", "priority": "high"},
]

def run():
    log.info("=== Lake Tahoe page watcher starting ===")
    changes = 0
    for page in WATCHED_PAGES:
        try:
            if watch_page(page["name"], page["url"], CITY, page["priority"]):
                changes += 1
        except Exception as e:
            log.error("Error watching %s: %s", page["name"], e)
    log.info("Lake Tahoe page watcher done — checked: %d | changed: %d", len(WATCHED_PAGES), changes)
    return {"checked": len(WATCHED_PAGES), "changes": changes}

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print(run())
