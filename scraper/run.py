"""
run.py — STRWatch scraper orchestrator.

Run manually: python3 run.py
With cron:    0 8 * * * cd /path/to/strwatch-scraper && python3 run.py

Flags:
  --full-sync       Re-sync Denver from scratch (use on first run)
  --denver-only     Only run Denver SODA scraper
  --nashville-only  Only run Nashville Legistar scraper
  --austin-only     Only run Austin scraper
  --nola-only       Only run New Orleans scrapers
  --indianapolis-only  Only run Indianapolis scrapers
  --pages-only      Only run generic page watcher
  --dump-fields     Print Denver SODA API field names (for FIELD_MAP setup)
  --dry-run         Run scrapers but skip sending alerts
  --reminders-only  Only run deadline reminders
"""

from typing import Callable, List, Optional, Tuple
import importlib
import os
import sys
import logging
import time
import traceback
from datetime import datetime, timezone

# Configure logging before imports
log_level = logging.DEBUG if "--debug" in sys.argv else logging.INFO
logging.basicConfig(
    level=log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("strwatch")

import config
from db import store


def banner(text: str):
    width = 60
    log.info("=" * width)
    log.info(f"  {text}")
    log.info("=" * width)


# ── scrape_runs log ───────────────────────────────────────────────────────────
# One row per scraper/source per run (supabase/migrations/*_scrape_runs.sql).
# Writing this row must never abort the run: every failure is logged and
# swallowed.

SOURCE_CITY = {
    "denver": "Denver, CO",
    "nashville": "Nashville, TN",
    "austin": "Austin, TX",
    "austin_soda": "Austin, TX",
    "scottsdale": "Scottsdale, AZ",
    "palm_springs": "Palm Springs, CA",
    "nola_legistar": "New Orleans, LA",
    "nola_soda": "New Orleans, LA",
    "sandiego": "San Diego, CA",
    "charleston": "Charleston, SC",
    "savannah": "Savannah, GA",
    "sf": "San Francisco, CA",
    "miamibeach": "Miami Beach, FL",
    "gatlinburg": "Gatlinburg, TN",
    "asheville": "Asheville, NC",
    "keywest": "Key West, FL",
    "sedona": "Sedona, AZ",
    "parkcity": "Park City, UT",
    "breckenridge": "Breckenridge, CO",
    "bigbear": "Big Bear, CA",
    "hawaii": "Hawaii",
    "outerbanks": "Outer Banks, NC",
    "nyc": "New York City, NY",
    "la": "Los Angeles, CA",
    "orlando": "Orlando, FL",
    "lasvegas": "Las Vegas, NV",
    "boston": "Boston, MA",
    "portland": "Portland, OR",
    "destin": "Destin, FL",
    "maui": "Maui, HI",
    "tybee": "Tybee Island, GA",
    "laketahoe": "Lake Tahoe, CA",
    "indianapolis": "Indianapolis, IN",
    # multi-market sources: city left NULL
    "state_pages": None,
    "county_pages": None,
    "legistar_multi": None,
}

# Result-dict keys that mean "this run found something new".
CHANGE_KEYS = ("changes", "page_changes", "new", "revoked", "new_bills",
               "new_agenda_items", "new_legislation", "total_new_bills")
ERROR_KEYS = ("errors", "total_errors")


def _as_int(value) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, (list, tuple, set, dict)):
        return len(value)
    return 0


def classify_result(result) -> Tuple[str, int]:
    """Map a scraper's result dict to (status, pages_changed)."""
    if not isinstance(result, dict):
        return "ok", 0
    changed = sum(_as_int(result.get(k, 0)) for k in CHANGE_KEYS)
    return ("changed" if changed > 0 else "ok"), changed


def result_error_count(result) -> int:
    if not isinstance(result, dict):
        return 0
    if "error" in result and result.get("error"):
        return 1
    return sum(_as_int(result.get(k, 0)) for k in ERROR_KEYS)


def record_scrape_run(source: str, city: Optional[str], started_at: datetime,
                      status: str, pages_changed: int = 0,
                      error: Optional[str] = None) -> bool:
    """Insert one scrape_runs row. Never raises."""
    try:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            log.debug("scrape_runs: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set — skipping")
            return False
        import requests
        payload = {
            "source": source,
            "city": city,
            "started_at": started_at.isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "pages_changed": int(pages_changed or 0),
            "error": (error[:500] if error else None),
        }
        resp = requests.post(
            f"{url}/rest/v1/scrape_runs",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            json=payload,
            timeout=10,
        )
        if not resp.ok:
            log.warning("scrape_runs insert failed for %s: %s %s", source, resp.status_code, resp.text[:200])
            return False
        return True
    except Exception as e:  # noqa: BLE001 — must never abort the run
        log.warning("scrape_runs insert error for %s: %s", source, e)
        return False


def run_step(results: dict, key: str, title: str, module_name: str, label: str,
             call: Callable = lambda m: m.run()) -> None:
    """Run one scraper, store its result under results[key], log a scrape_runs row.

    Behaviour matches the old inline try/except blocks: exceptions are logged
    with traceback and recorded as {"error": str(e)}.
    """
    banner(title)
    started = datetime.now(timezone.utc)
    status, changed, error = "ok", 0, None
    try:
        module = importlib.import_module(module_name)
        result = call(module)
        results[key] = result
        status, changed = classify_result(result)
    except Exception as e:
        log.error("%s failed: %s", label, e, exc_info=True)
        results[key] = {"error": str(e)}
        status, changed, error = "error", 0, traceback.format_exc()[:500]

    try:
        record_scrape_run(key, SOURCE_CITY.get(key), started, status, changed, error)
    except Exception as e:  # noqa: BLE001 — logging must never abort the run
        log.warning("scrape_runs write failed for %s: %s", key, e)


def run_all(args: List[str]) -> dict:
    start = time.time()
    results = {}

    # ── Init DB ──
    store.init_db()

    full_sync = "--full-sync" in args
    dry_run = "--dry-run" in args
    reminders_only = "--reminders-only" in args

    if dry_run:
        log.warning("DRY RUN MODE — alerts will not be sent")
        # Monkey-patch alert functions
        import alerts.notify as _n
        _n.send_email = lambda *a, **k: log.info("DRY RUN: would send email: %s", a[0] if a else "")
        _n.send_sms = lambda *a, **k: log.info("DRY RUN: would send SMS: %s", str(a)[:80])

    # ── Reminders only mode ──
    if reminders_only:
        banner("Deadline Reminders")
        try:
            from alerts import reminders
            results["reminders"] = reminders.check_and_send_reminders()
        except Exception as e:
            log.error("Reminder check failed: %s", e, exc_info=True)
            results["reminders"] = {"error": str(e)}
        banner("Run Complete")
        return results

    # ── Denver SODA ──
    if "--nashville-only" not in args and "--austin-only" not in args and "--pages-only" not in args and "--indianapolis-only" not in args:
        if "--dump-fields" in args:
            banner("Denver SODA API")
            from scrapers import denver_soda
            denver_soda.dump_fields()
            return {}
        run_step(results, "denver", "Denver SODA API", "scrapers.denver_soda", "Denver scraper",
                 call=lambda m: m.run(full_sync=full_sync))

    # ── Nashville Legistar ──
    if "--denver-only" not in args and "--austin-only" not in args and "--pages-only" not in args and "--indianapolis-only" not in args:
        run_step(results, "nashville", "Nashville Legistar", "scrapers.nashville_legistar", "Nashville scraper", call=lambda m: m.run(days_back=14))

    # ── Austin + all other city scrapers ──
    if "--denver-only" not in args and "--nashville-only" not in args and "--pages-only" not in args and "--indianapolis-only" not in args:
        run_step(results, "austin", "Austin Web Scraper", "scrapers.austin_web", "Austin scraper")

        run_step(results, "scottsdale", "Scottsdale ArcGIS Licenses", "scrapers.scottsdale_arcgis", "Scottsdale scraper")

        run_step(results, "palm_springs", "Palm Springs Web Watcher", "scrapers.palm_springs_web", "Palm Springs scraper")

        run_step(results, "austin_soda", "Austin SODA Licenses", "scrapers.austin_soda", "Austin SODA scraper")

        run_step(results, "nola_legistar", "New Orleans Legistar", "scrapers.nola_legistar", "NOLA Legistar scraper", call=lambda m: m.run(days_back=14))

        run_step(results, "nola_soda", "New Orleans SODA Licenses", "scrapers.nola_soda", "NOLA SODA scraper", call=lambda m: m.run(full_sync=full_sync))

        run_step(results, "sandiego", "San Diego STRO Page Watcher", "scrapers.sandiego_web", "San Diego scraper")

        run_step(results, "charleston", "Charleston SC Page Watcher", "scrapers.charleston_web", "Charleston scraper")

        run_step(results, "savannah", "Savannah GA Page Watcher", "scrapers.savannah_web", "Savannah scraper")

        run_step(results, "sf", "San Francisco Page Watcher", "scrapers.sf_web", "SF scraper")

        run_step(results, "miamibeach", "Miami Beach Page Watcher", "scrapers.miamibeach_web", "Miami Beach scraper")

        run_step(results, "gatlinburg", "Gatlinburg TN Page Watcher", "scrapers.gatlinburg_web", "Gatlinburg scraper")

        run_step(results, "asheville", "Asheville NC Page Watcher", "scrapers.asheville_web", "Asheville scraper")

        run_step(results, "keywest", "Key West FL Page Watcher", "scrapers.keywest_web", "Key West scraper")

        run_step(results, "sedona", "Sedona AZ Page Watcher", "scrapers.sedona_web", "Sedona scraper")

        run_step(results, "parkcity", "Park City UT Page Watcher", "scrapers.parkcity_web", "Park City scraper")

        run_step(results, "breckenridge", "Breckenridge CO Page Watcher", "scrapers.breckenridge_web", "Breckenridge scraper")

        run_step(results, "bigbear", "Big Bear CA Page Watcher", "scrapers.bigbear_web", "Big Bear scraper")

        run_step(results, "hawaii", "Hawaii Page Watcher", "scrapers.hawaii_web", "Hawaii scraper")

        run_step(results, "outerbanks", "Outer Banks NC Page Watcher", "scrapers.outerbanks_web", "Outer Banks scraper")

        # ── Markets #21-30 (added March 2026) ──

        run_step(results, "nyc", "New York City NY Page Watcher", "scrapers.nyc_web", "NYC scraper")

        run_step(results, "la", "Los Angeles CA Page Watcher", "scrapers.la_web", "LA scraper")

        run_step(results, "orlando", "Orlando FL Page Watcher", "scrapers.orlando_web", "Orlando scraper")

        run_step(results, "lasvegas", "Las Vegas NV Page Watcher", "scrapers.lasvegas_web", "Las Vegas scraper")

        run_step(results, "boston", "Boston MA Page Watcher", "scrapers.boston_web", "Boston scraper")

        run_step(results, "portland", "Portland OR Page Watcher", "scrapers.portland_web", "Portland scraper")

        run_step(results, "destin", "Destin/30A FL Page Watcher", "scrapers.destin_web", "Destin scraper")

        run_step(results, "maui", "Maui HI Page Watcher", "scrapers.maui_web", "Maui scraper")

        run_step(results, "tybee", "Tybee Island GA Page Watcher", "scrapers.tybee_web", "Tybee Island scraper")

        run_step(results, "laketahoe", "Lake Tahoe CA Page Watcher", "scrapers.laketahoe_web", "Lake Tahoe scraper")

        # ── State-Level Pages (covers 20+ markets) ──

        run_step(results, "state_pages", "State-Level Pages (FL, HI, TN, AZ, GA)", "scrapers.state_pages_web", "State pages scraper")

    # ── Indianapolis ──
    if "--indianapolis-only" in args or (
        "--denver-only" not in args
        and "--nashville-only" not in args
        and "--austin-only" not in args
        and "--pages-only" not in args
    ):
        run_step(results, "indianapolis", "Indianapolis IN Page Watcher", "scrapers.indianapolis_web", "Indianapolis page watcher")

    # ── County-Level Pages (Davidson, Travis, El Dorado, Multnomah, Monroe, SB, Okaloosa, Chatham) ──
    run_step(results, "county_pages", "County-Level Pages (8 counties)", "scrapers.county_pages_web", "County pages scraper")

    # ── Multi-City Legistar (Denver, SF, Boston) ──
    run_step(results, "legistar_multi", "Multi-City Legistar (Denver, SF, Boston)", "scrapers.legistar_multi", "Multi-city Legistar scraper", call=lambda m: m.run(days_back=14))

    # ── Deadline Reminders (runs after all scrapers) ──
    banner("Deadline Reminders")
    try:
        from alerts import reminders
        results["reminders"] = reminders.check_and_send_reminders()
    except Exception as e:
        log.error("Reminder check failed: %s", e, exc_info=True)
        results["reminders"] = {"error": str(e)}

    banner("Run Complete")
    log.info("Run complete")
    log.info("Results:")
    for scraper, result in results.items():
        log.info("  %-15s %s", scraper + ":", result)

    return results


def exit_code(results: dict) -> int:
    """1 if any step raised ({"error": ...}) or reported errors > 0, else 0.

    (The old check was `"error" not in str(v)`, which matched the harmless
    `errors: 0` key and so exited 1 on every run.)
    """
    return 1 if any(result_error_count(v) > 0 for v in results.values()) else 0


if __name__ == "__main__":
    args = sys.argv[1:]
    banner(f"STRWatch Scraper — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    results = run_all(args)
    sys.exit(exit_code(results))
