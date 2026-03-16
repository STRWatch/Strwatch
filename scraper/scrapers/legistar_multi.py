"""
scrapers/legistar_multi.py — Multi-city Legistar legislation monitoring.

Generalizes the Nashville/NOLA Legistar pattern to monitor council legislation
across multiple cities using a single shared scraper.

Phase C cities (confirmed working Legistar API endpoints):
- Denver, CO — webapi.legistar.com/v1/denver
- San Francisco, CA — webapi.legistar.com/v1/sfgov
- Boston, MA — webapi.legistar.com/v1/boston

NOT included (API unavailable):
- NYC — requires API token (apply at council.nyc.gov/legislation/api/)
- Los Angeles — uses own CFMS system, not Legistar
- San Diego — city doesn't use Legistar (county does, wrong entity)

Each city is defined as a config dict with its Legistar slug, display name,
and Legistar web URL pattern. The scraper loops through all cities and runs
the same keyword-scan logic as Nashville/NOLA.
"""

from typing import Any, List, Optional
import logging
import requests
from datetime import datetime, timezone, timedelta

from scrapers.keywords import matches_keywords
import config
from db import store
from alerts import notify

log = logging.getLogger(__name__)

KEYWORDS = config.STR_KEYWORDS

# ── City definitions ──────────────────────────────────────────────────────────
# Each entry: slug used in API URL, display city name, Legistar web base
LEGISTAR_CITIES = [
    {
        "slug": "denver",
        "city": "Denver",
        "web_base": "https://denver.legistar.com",
        "priority": "high",
    },
    {
        "slug": "sfgov",
        "city": "San Francisco",
        "web_base": "https://sfgov.legistar.com",
        "priority": "high",
    },
    {
        "slug": "boston",
        "city": "Boston",
        "web_base": "https://boston.legistar.com",
        "priority": "medium",
    },
]


# ── API helpers ───────────────────────────────────────────────────────────────

def _get(base_url: str, path: str, params: dict = None) -> Optional[Any]:
    """Make a GET request to the Legistar API."""
    url = f"{base_url}{path}"
    headers = {"Accept": "application/json"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=20)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        log.error("Legistar HTTP error %s: %s", url, e)
    except Exception as e:
        log.error("Legistar request error %s: %s", url, e)
    return None


def _fetch_recent_legislation(base_url: str, city: str, days_back: int = 14) -> List[dict]:
    """Fetch legislation introduced in the last N days for a given city."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00")

    params = {
        "$filter": f"MatterIntroDate ge datetime'{cutoff}'",
        "$orderby": "MatterIntroDate desc",
        "$top": 200,
    }

    log.debug("Fetching %s legislation since %s", city, cutoff)
    results = _get(base_url, "/Matters", params=params)
    if not results:
        return []

    log.info("%s Legistar: %d items in last %d days", city, len(results), days_back)
    return results


def _fetch_legislation_text(base_url: str, matter_id: int) -> str:
    """Fetch full text of a matter for keyword scanning."""
    files = _get(base_url, f"/Matters/{matter_id}/MatterTexts")
    if not files:
        return ""
    texts = []
    for f in files:
        t = f.get("MatterTextPlain") or f.get("MatterTextRtf") or ""
        texts.append(t)
    return " ".join(texts)


def _get_matter_url(web_base: str, matter_id: int) -> str:
    """Build the public-facing Legistar URL for a given matter."""
    return f"{web_base}/LegislationDetail.aspx?ID={matter_id}&GUID=&Search="


# ── Per-city scan ─────────────────────────────────────────────────────────────

def scan_city(city_config: dict, days_back: int = 14) -> dict:
    """
    Scan one city's Legistar API for STR-related legislation.
    Returns dict with checked, str_matches, new_bills, errors counts.
    """
    slug = city_config["slug"]
    city = city_config["city"]
    web_base = city_config["web_base"]
    base_url = f"https://webapi.legistar.com/v1/{slug}"

    log.info("--- Scanning %s (slug: %s) ---", city, slug)

    matters = _fetch_recent_legislation(base_url, city, days_back=days_back)
    new_bills = []
    total_str_matches = 0
    checked = 0
    errors = 0

    for matter in matters:
        checked += 1
        matter_id = matter.get("MatterId")
        title = matter.get("MatterTitle", "") or ""
        matter_type = matter.get("MatterTypeName", "") or ""
        status = matter.get("MatterStatusName", "") or ""
        intro_date = matter.get("MatterIntroDate", "") or ""
        bill_id = matter.get("MatterFile") or str(matter_id)
        url = _get_matter_url(web_base, matter_id)

        # Quick title scan first (fast)
        title_matches = matches_keywords(title, KEYWORDS)

        # If title matches, also scan full text for more context
        body_matches = []
        if title_matches or any(kw.lower() in matter_type.lower() for kw in ["rental", "str", "lodging", "airbnb"]):
            try:
                text = _fetch_legislation_text(base_url, matter_id)
                body_matches = matches_keywords(text, KEYWORDS)
            except Exception as e:
                errors += 1
                log.warning("Could not fetch text for %s matter %s: %s", city, matter_id, e)

        all_matches = list(set(title_matches + body_matches))
        if not all_matches:
            continue

        total_str_matches += 1
        log.info("STR match: [%s] %s — %s (keywords: %s)", city, bill_id, title[:80], all_matches[:3])

        try:
            is_new = store.save_legislation(
                city=city,
                source="Legistar",
                bill_id=str(bill_id),
                title=title,
                description=matter.get("MatterBodyName", ""),
                status=status,
                introduced_date=intro_date[:10] if intro_date else "",
                url=url,
                keyword_matches=all_matches,
                raw=matter,
            )
            if is_new:
                new_bills.append({
                    "bill_id": bill_id,
                    "title": title,
                    "url": url,
                    "keywords": all_matches,
                    "city": city,
                })
        except Exception as e:
            errors += 1
            log.error("DB error for %s matter %s: %s", city, matter_id, e)

    log.info("%s Legistar done — checked: %d | STR matches: %d | new: %d | errors: %d",
             city, checked, total_str_matches, len(new_bills), errors)

    # Alert on each new bill
    for bill in new_bills:
        notify.alert_new_legislation(
            city=bill["city"],
            bill_id=bill["bill_id"],
            title=bill["title"],
            url=bill["url"],
            keywords=bill["keywords"],
        )

    return {
        "city": city,
        "checked": checked,
        "str_matches": total_str_matches,
        "new_bills": len(new_bills),
        "errors": errors,
    }


# ── Main run function ─────────────────────────────────────────────────────────

def run(days_back: int = 14):
    """
    Main entry point. Scan all configured Legistar cities for STR legislation.
    """
    log.info("=== Multi-city Legistar scraper starting (%d cities, last %d days) ===",
             len(LEGISTAR_CITIES), days_back)

    results_by_city = {}
    total_new = 0
    total_errors = 0

    for city_config in LEGISTAR_CITIES:
        try:
            result = scan_city(city_config, days_back=days_back)
            results_by_city[result["city"]] = result
            total_new += result["new_bills"]
            total_errors += result["errors"]
        except Exception as e:
            city = city_config["city"]
            log.error("%s Legistar scan failed: %s", city, e)
            results_by_city[city] = {"error": str(e)}
            total_errors += 1

    log.info("Multi-city Legistar done — cities: %d | total new bills: %d | total errors: %d",
             len(LEGISTAR_CITIES), total_new, total_errors)

    return {
        "cities_scanned": len(LEGISTAR_CITIES),
        "total_new_bills": total_new,
        "total_errors": total_errors,
        "by_city": results_by_city,
    }


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.DEBUG)
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    result = run(days_back=days)
    print(f"\nResult: {result}")
