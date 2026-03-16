"""
scrapers/county_pages_web.py — County-level STR regulatory page monitoring.

Watches county government pages for STR permit, tax, and licensing changes.
Each county page covers one or more STRWatch markets:

- Davidson County, TN (Nashville) — County Clerk STR business license + Codes Dept
- Travis County / Austin, TX — Hotel Occupancy Tax pages
- El Dorado County, CA (Lake Tahoe) — VHR program + applications
- Multnomah County, OR (Portland) — Transient lodging tax
- Monroe County, FL (Key West) — Tourist Development Tax
- San Bernardino County, CA (Big Bear) — STR permit program
- Okaloosa County, FL (Destin/30A) — Tourist Development Tax
- Chatham County, GA (Savannah + Tybee Island) — Hotel/Motel tax + STR certificates

Phase B of the jurisdiction audit. ~20 URLs across 8 counties.
"""

import logging
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)

# ── Davidson County, TN (Nashville) ──────────────────────────────────────────
# Nashville is a consolidated city-county (Metro Nashville-Davidson County).
# County Clerk handles STR business tax licenses; Codes Dept handles permits.
DAVIDSON_COUNTY_PAGES = [
    {
        "name": "Davidson County Clerk — STR Business License",
        "url": "https://www.nashville.gov/departments/county-clerk/business-services/short-term-rental-property-business-license",
        "city": "Nashville",
        "priority": "high",
    },
    {
        "name": "Nashville Codes — STR Hub Page",
        "url": "https://www.nashville.gov/departments/codes/short-term-rentals",
        "city": "Nashville",
        "priority": "high",
    },
    {
        "name": "Nashville Codes — STR Permit Application",
        "url": "https://www.nashville.gov/departments/codes/short-term-rentals/apply-short-term-rental-property-permit",
        "city": "Nashville",
        "priority": "medium",
    },
]

# ── Travis County / Austin, TX ────────────────────────────────────────────────
# Austin administers its own Hotel Occupancy Tax (11% city + 6% state).
# Travis County has no separate county STR tax, but Austin's HOT pages are critical.
TRAVIS_COUNTY_PAGES = [
    {
        "name": "Austin — Hotel and Rental Tax Overview",
        "url": "https://www.austintexas.gov/page/hotel-and-rental-tax",
        "city": "Austin",
        "priority": "high",
    },
    {
        "name": "Austin — Hotel Occupancy Tax Rates & Filing",
        "url": "https://www.austintexas.gov/page/hotel-occupancy-taxes",
        "city": "Austin",
        "priority": "high",
    },
]

# ── El Dorado County, CA (Lake Tahoe) ────────────────────────────────────────
# Active VHR program with 500ft buffer, permit caps, and $564 new permit fees.
# Ordinance effective 11/21/24. Very active regulation — check frequently.
ELDORADO_COUNTY_PAGES = [
    {
        "name": "El Dorado County — VHR Division Main Page",
        "url": "https://www.eldoradocounty.ca.gov/Services/My-Property/Vacation-Home-Rentals-Division",
        "city": "Lake Tahoe",
        "priority": "high",
    },
    {
        "name": "El Dorado County — VHR Applications, Forms & Policies",
        "url": "https://www.eldoradocounty.ca.gov/Services/My-Property/Vacation-Home-Rentals-Division/VHR-Applications-Forms-and-Policies",
        "city": "Lake Tahoe",
        "priority": "high",
    },
    {
        "name": "El Dorado County — VHR Ordinance Info",
        "url": "https://www.eldoradocounty.ca.gov/Services/My-Property/Vacation-Home-Rentals-Division/VHR-Ordinance-Information",
        "city": "Lake Tahoe",
        "priority": "high",
    },
]

# ── Multnomah County, OR (Portland) ──────────────────────────────────────────
# Portland + Multnomah County combined 11.5% transient lodging tax.
# $4/night STR fee funds affordable housing. Quarterly filing.
MULTNOMAH_COUNTY_PAGES = [
    {
        "name": "Multnomah County — Transient Lodging Tax",
        "url": "https://multco.us/info/multnomah-county-transient-lodging-tax",
        "city": "Portland",
        "priority": "high",
    },
    {
        "name": "Portland Revenue — Transient Lodgings Tax Filing",
        "url": "https://www.portland.gov/revenue/transient-lodgings-tax",
        "city": "Portland",
        "priority": "high",
    },
]

# ── Monroe County, FL (Key West) ─────────────────────────────────────────────
# 5% Tourist Development Tax on rentals ≤ 6 months. Monthly filing.
# No agreement with Airbnb/VRBO — hosts must remit directly.
MONROE_COUNTY_PAGES = [
    {
        "name": "Monroe County Tax Collector — Tourist Development Tax",
        "url": "https://monroetaxcollector.com/services/tdt/",
        "city": "Key West",
        "priority": "medium",
    },
]

# ── San Bernardino County, CA (Big Bear) ─────────────────────────────────────
# Active STR permit program with $1,144 new application fee.
# Noise monitoring program, 24/7 complaint hotline. Mountain & Desert regions.
SAN_BERNARDINO_COUNTY_PAGES = [
    {
        "name": "San Bernardino County — STR Program Home",
        "url": "https://str.sbcounty.gov/",
        "city": "Big Bear",
        "priority": "medium",
    },
    {
        "name": "San Bernardino County — STR Getting Started",
        "url": "https://str.sbcounty.gov/getting-started/",
        "city": "Big Bear",
        "priority": "medium",
    },
    {
        "name": "San Bernardino County — STR Permitted Properties Map",
        "url": "https://str.sbcounty.gov/permitted-str-properties/",
        "city": "Big Bear",
        "priority": "low",
    },
]

# ── Okaloosa County, FL (Destin/30A) ─────────────────────────────────────────
# 6% Tourist Development Tax (current district). Monthly filing.
# Not contracted with Airbnb/VRBO — hosts responsible for remitting.
OKALOOSA_COUNTY_PAGES = [
    {
        "name": "Okaloosa County Clerk — Tourist Development Tax",
        "url": "https://okaloosaclerk.com/board-services/tourist-development-tax/",
        "city": "Destin",
        "priority": "medium",
    },
    {
        "name": "Okaloosa County — Tourist Tax FAQ",
        "url": "https://okaloosaclerk.com/board-services/tourist-development-tax/tourist-development-tax-faq/",
        "city": "Destin",
        "priority": "low",
    },
]

# ── Chatham County, GA (Savannah + Tybee Island) ─────────────────────────────
# 8% hotel/motel excise tax (Savannah, effective Sept 2023).
# STR certificate required in unincorporated Chatham County ($350/yr).
# Savannah has 20% cap per ward in historic districts.
CHATHAM_COUNTY_PAGES = [
    {
        "name": "Savannah — Local & State Taxes (Hotel/Motel)",
        "url": "https://www.savannahga.gov/2328/Local-State-Taxes",
        "city": "Savannah",
        "priority": "medium",
    },
    {
        "name": "Savannah — Short-Term Vacation Rentals",
        "url": "https://www.savannahga.gov/1476/Short-Term-Vacation-Rentals",
        "city": "Savannah",
        "priority": "high",
    },
]

# ── All pages combined ────────────────────────────────────────────────────────
ALL_COUNTY_PAGES = (
    DAVIDSON_COUNTY_PAGES
    + TRAVIS_COUNTY_PAGES
    + ELDORADO_COUNTY_PAGES
    + MULTNOMAH_COUNTY_PAGES
    + MONROE_COUNTY_PAGES
    + SAN_BERNARDINO_COUNTY_PAGES
    + OKALOOSA_COUNTY_PAGES
    + CHATHAM_COUNTY_PAGES
)


def run():
    """Watch all county-level STR regulatory pages."""
    log.info(
        "=== County-level page watcher starting (%d pages across 8 counties) ===",
        len(ALL_COUNTY_PAGES),
    )

    changes = 0
    errors = 0
    results_by_county = {}

    for page in ALL_COUNTY_PAGES:
        try:
            changed = watch_page(
                name=page["name"],
                url=page["url"],
                city=page["city"],
                priority=page["priority"],
            )
            if changed:
                changes += 1

            # Track per-county results
            county = page["city"]
            if county not in results_by_county:
                results_by_county[county] = {"checked": 0, "changed": 0}
            results_by_county[county]["checked"] += 1
            if changed:
                results_by_county[county]["changed"] += 1

        except Exception as e:
            errors += 1
            log.error("Error watching %s: %s", page["name"], e)

    log.info(
        "County-level page watcher done — checked: %d | changed: %d | errors: %d",
        len(ALL_COUNTY_PAGES),
        changes,
        errors,
    )
    for county, stats in results_by_county.items():
        log.info("  %s: checked %d, changed %d", county, stats["checked"], stats["changed"])

    return {
        "checked": len(ALL_COUNTY_PAGES),
        "changes": changes,
        "errors": errors,
        "by_county": results_by_county,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    result = run()
    print(f"\nResult: {result}")
