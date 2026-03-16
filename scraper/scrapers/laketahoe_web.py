"""
scrapers/laketahoe_web.py — Lake Tahoe CA/NV STR page monitoring.

Lake Tahoe spans multiple jurisdictions with complex STR rules:
  - El Dorado County (South Lake Tahoe, CA): VHR permit required,
    lottery for new permits, caps by neighborhood
  - Placer County (North Shore, CA): STR permit moratorium in some areas,
    active enforcement, $1,000/day fines
  - Washoe County (NV side, Incline Village): residential permit required
  - City of South Lake Tahoe: Measure T passed 2018 (banned non-owner STRs
    in residential), later modified by Measure N (2024)
  - TRPA (Tahoe Regional Planning Agency): additional environmental overlays
  - TOT rates vary: 10-14% depending on jurisdiction
  - Aggressive enforcement with dedicated STR enforcement staff
  - Bear box and wildlife management requirements

Data sources:
  - South Lake Tahoe: cityofslt.us/585/Vacation-Home-Rental-VHR-Program
  - El Dorado County: edcgov.us/VHR
  - Placer County: placer.ca.gov/str
  - Washoe County: washoecounty.gov/building/str
"""

import logging
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)
CITY = "Lake Tahoe, CA"

WATCHED_PAGES = [
    {"name": "South Lake Tahoe — VHR Program", "url": "https://www.cityofslt.us/585/Vacation-Home-Rental-VHR-Program", "priority": "high"},
    {"name": "El Dorado County — VHR Permits", "url": "https://www.edcgov.us/Government/Planning/vacation-home-rentals", "priority": "high"},
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
