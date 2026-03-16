"""
scrapers/state_pages_web.py — Shared state-level STR regulatory page monitoring.

Watches state tax authority and licensing pages that cover MULTIPLE markets each:
- FL DBPR (Miami Beach, Orlando, Key West, Destin/30A)
- HI DOTAX (Honolulu, Maui)
- TN DOR (Nashville, Gatlinburg)
- AZ DOR (Scottsdale, Sedona)
- GA DOR (Savannah, Tybee Island)
- CA — no single state page; TOT is city/county administered (handled separately)

One scraper, ~15 URLs, covers state-level regulatory changes for 20+ markets.
"""

import logging
from scrapers.austin_web import watch_page

log = logging.getLogger(__name__)

# ── Florida DBPR ──────────────────────────────────────────────────────────────
# Covers: Miami Beach, Orlando, Key West, Destin/30A
# State vacation rental licensing authority (Chapter 509, F.S.)
FL_DBPR_PAGES = [
    {
        "name": "FL DBPR — Vacation Rental & Timeshare Guide",
        "url": "https://www2.myfloridalicense.com/hotels-restaurants/licensing/vrtsp-guide/",
        "city": "Florida (statewide)",
        "priority": "high",
    },
    {
        "name": "FL DBPR — Hotels & Restaurants Division",
        "url": "https://www2.myfloridalicense.com/hotels-restaurants/",
        "city": "Florida (statewide)",
        "priority": "high",
    },
    {
        "name": "FL DBPR — New Vacation Rental Dwelling License Checklist",
        "url": "https://www.myfloridalicense.com/CheckListDetail.asp?SID=&xactCode=1030&clientCode=2007&XACT_DEFN_ID=7694",
        "city": "Florida (statewide)",
        "priority": "medium",
    },
]

# ── Hawaii DOTAX ──────────────────────────────────────────────────────────────
# Covers: Honolulu, Maui
# State GET + TAT registration and compliance
HI_DOTAX_PAGES = [
    {
        "name": "HI DOTAX — Renting Residential Real Property",
        "url": "https://tax.hawaii.gov/rental/",
        "city": "Hawaii (statewide)",
        "priority": "high",
    },
    {
        "name": "HI DOTAX — TAT Forms & Filing",
        "url": "https://tax.hawaii.gov/forms/a1_b2_2tat/",
        "city": "Hawaii (statewide)",
        "priority": "medium",
    },
]

# ── Tennessee DOR ─────────────────────────────────────────────────────────────
# Covers: Nashville, Gatlinburg
# State sales tax + local occupancy tax for STRs
TN_DOR_PAGES = [
    {
        "name": "TN DOR — Local Occupancy Tax",
        "url": "https://www.tn.gov/revenue/taxes/local-occupancy-tax.html",
        "city": "Tennessee (statewide)",
        "priority": "high",
    },
    {
        "name": "TN DOR — Local Occupancy Tax Registration",
        "url": "https://www.tn.gov/revenue/taxes/local-occupancy-tax/registration.html",
        "city": "Tennessee (statewide)",
        "priority": "medium",
    },
]

# ── Arizona DOR ───────────────────────────────────────────────────────────────
# Covers: Scottsdale, Sedona
# TPT for short-term lodging (< 30 days)
AZ_DOR_PAGES = [
    {
        "name": "AZ DOR — Short-Term Lodging TPT",
        "url": "https://azdor.gov/business/transaction-privilege-tax/short-term-lodging",
        "city": "Arizona (statewide)",
        "priority": "high",
    },
    {
        "name": "AZ DOR — Online Lodging Marketplace",
        "url": "https://azdor.gov/business/transaction-privilege-tax/online-lodging-marketplace",
        "city": "Arizona (statewide)",
        "priority": "medium",
    },
    {
        "name": "AZ DOR — TPT Reporting Guide",
        "url": "https://azdor.gov/business/transaction-privilege-tax/reporting-guide",
        "city": "Arizona (statewide)",
        "priority": "medium",
    },
]

# ── Georgia DOR ───────────────────────────────────────────────────────────────
# Covers: Savannah, Tybee Island
# State hotel-motel fee ($5/night) + sales tax on accommodations
GA_DOR_PAGES = [
    {
        "name": "GA DOR — State Hotel-Motel Fee",
        "url": "https://dor.georgia.gov/taxes/taxes-business/other-business-taxes/state-hotel-motel-fee",
        "city": "Georgia (statewide)",
        "priority": "high",
    },
    {
        "name": "GA DOR — Hotel-Motel Fee Registration Guide",
        "url": "https://dor.georgia.gov/how-register-state-hotel-motel-fee-account",
        "city": "Georgia (statewide)",
        "priority": "medium",
    },
]

# ── All pages combined ────────────────────────────────────────────────────────
ALL_STATE_PAGES = FL_DBPR_PAGES + HI_DOTAX_PAGES + TN_DOR_PAGES + AZ_DOR_PAGES + GA_DOR_PAGES


def run():
    """Watch all state-level STR regulatory pages."""
    log.info("=== State-level page watcher starting (%d pages across 5 states) ===", len(ALL_STATE_PAGES))

    changes = 0
    errors = 0
    results_by_state = {}

    for page in ALL_STATE_PAGES:
        try:
            changed = watch_page(
                name=page["name"],
                url=page["url"],
                city=page["city"],
                priority=page["priority"],
            )
            if changed:
                changes += 1

            # Track per-state results
            state = page["city"].split("(")[0].strip()
            if state not in results_by_state:
                results_by_state[state] = {"checked": 0, "changed": 0}
            results_by_state[state]["checked"] += 1
            if changed:
                results_by_state[state]["changed"] += 1

        except Exception as e:
            errors += 1
            log.error("Error watching %s: %s", page["name"], e)

    log.info(
        "State-level page watcher done — checked: %d | changed: %d | errors: %d",
        len(ALL_STATE_PAGES), changes, errors
    )
    for state, stats in results_by_state.items():
        log.info("  %s: checked %d, changed %d", state, stats["checked"], stats["changed"])

    return {
        "checked": len(ALL_STATE_PAGES),
        "changes": changes,
        "errors": errors,
        "by_state": results_by_state,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    result = run()
    print(f"\nResult: {result}")
