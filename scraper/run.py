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
  --pages-only      Only run generic page watcher
  --dump-fields     Print Denver SODA API field names (for FIELD_MAP setup)
  --dry-run         Run scrapers but skip sending alerts
  --reminders-only  Only run deadline reminders
"""

from typing import List
import sys
import logging
import time
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
    if "--nashville-only" not in args and "--austin-only" not in args and "--pages-only" not in args:
        banner("Denver SODA API")
        try:
            from scrapers import denver_soda
            if "--dump-fields" in args:
                denver_soda.dump_fields()
                return {}
            results["denver"] = denver_soda.run(full_sync=full_sync)
        except Exception as e:
            log.error("Denver scraper failed: %s", e, exc_info=True)
            results["denver"] = {"error": str(e)}

    # ── Nashville Legistar ──
    if "--denver-only" not in args and "--austin-only" not in args and "--pages-only" not in args:
        banner("Nashville Legistar")
        try:
            from scrapers import nashville_legistar
            results["nashville"] = nashville_legistar.run(days_back=14)
        except Exception as e:
            log.error("Nashville scraper failed: %s", e, exc_info=True)
            results["nashville"] = {"error": str(e)}

    # ── Austin ──
    if "--denver-only" not in args and "--nashville-only" not in args and "--pages-only" not in args:
        banner("Austin Web Scraper")
        try:
            from scrapers import austin_web
            results["austin"] = austin_web.run()
        except Exception as e:
            log.error("Austin scraper failed: %s", e, exc_info=True)
            results["austin"] = {"error": str(e)}

        banner("Scottsdale ArcGIS Licenses")
        try:
            from scrapers import scottsdale_arcgis
            results["scottsdale"] = scottsdale_arcgis.run()
        except Exception as e:
            log.error("Scottsdale scraper failed: %s", e, exc_info=True)
            results["scottsdale"] = {"error": str(e)}

        banner("Palm Springs Web Watcher")
        try:
            from scrapers import palm_springs_web
            results["palm_springs"] = palm_springs_web.run()
        except Exception as e:
            log.error("Palm Springs scraper failed: %s", e, exc_info=True)
            results["palm_springs"] = {"error": str(e)}

        banner("Austin SODA Licenses")
        try:
            from scrapers import austin_soda
            results["austin_soda"] = austin_soda.run()
        except Exception as e:
            log.error("Austin SODA scraper failed: %s", e, exc_info=True)
            results["austin_soda"] = {"error": str(e)}

        banner("New Orleans Legistar")
        try:
            from scrapers import nola_legistar
            results["nola_legistar"] = nola_legistar.run(days_back=14)
        except Exception as e:
            log.error("NOLA Legistar scraper failed: %s", e, exc_info=True)
            results["nola_legistar"] = {"error": str(e)}

        banner("New Orleans SODA Licenses")
        try:
            from scrapers import nola_soda
            results["nola_soda"] = nola_soda.run(full_sync=full_sync)
        except Exception as e:
            log.error("NOLA SODA scraper failed: %s", e, exc_info=True)
            results["nola_soda"] = {"error": str(e)}

        banner("San Diego STRO Page Watcher")
        try:
            from scrapers import sandiego_web
            results["sandiego"] = sandiego_web.run()
        except Exception as e:
            log.error("San Diego scraper failed: %s", e, exc_info=True)
            results["sandiego"] = {"error": str(e)}

        banner("Charleston SC Page Watcher")
        try:
            from scrapers import charleston_web
            results["charleston"] = charleston_web.run()
        except Exception as e:
            log.error("Charleston scraper failed: %s", e, exc_info=True)
            results["charleston"] = {"error": str(e)}

        banner("Savannah GA Page Watcher")
        try:
            from scrapers import savannah_web
            results["savannah"] = savannah_web.run()
        except Exception as e:
            log.error("Savannah scraper failed: %s", e, exc_info=True)
            results["savannah"] = {"error": str(e)}

        banner("San Francisco Page Watcher")
        try:
            from scrapers import sf_web
            results["sf"] = sf_web.run()
        except Exception as e:
            log.error("SF scraper failed: %s", e, exc_info=True)
            results["sf"] = {"error": str(e)}

        banner("Miami Beach Page Watcher")
        try:
            from scrapers import miamibeach_web
            results["miamibeach"] = miamibeach_web.run()
        except Exception as e:
            log.error("Miami Beach scraper failed: %s", e, exc_info=True)
            results["miamibeach"] = {"error": str(e)}

        banner("Gatlinburg TN Page Watcher")
        try:
            from scrapers import gatlinburg_web
            results["gatlinburg"] = gatlinburg_web.run()
        except Exception as e:
            log.error("Gatlinburg scraper failed: %s", e, exc_info=True)
            results["gatlinburg"] = {"error": str(e)}

        banner("Asheville NC Page Watcher")
        try:
            from scrapers import asheville_web
            results["asheville"] = asheville_web.run()
        except Exception as e:
            log.error("Asheville scraper failed: %s", e, exc_info=True)
            results["asheville"] = {"error": str(e)}

        banner("Key West FL Page Watcher")
        try:
            from scrapers import keywest_web
            results["keywest"] = keywest_web.run()
        except Exception as e:
            log.error("Key West scraper failed: %s", e, exc_info=True)
            results["keywest"] = {"error": str(e)}

        banner("Sedona AZ Page Watcher")
        try:
            from scrapers import sedona_web
            results["sedona"] = sedona_web.run()
        except Exception as e:
            log.error("Sedona scraper failed: %s", e, exc_info=True)
            results["sedona"] = {"error": str(e)}

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


if __name__ == "__main__":
    args = sys.argv[1:]
    banner(f"STRWatch Scraper — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    results = run_all(args)
    sys.exit(0 if all("error" not in str(v) for v in results.values()) else 1)
