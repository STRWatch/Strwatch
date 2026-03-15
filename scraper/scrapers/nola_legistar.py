"""
scrapers/nola_legistar.py — New Orleans City Council legislation via Legistar API.

New Orleans uses Legistar (webapi.legistar.com/v1/cityofno).
- Searches for STR-related legislation by keyword
- Detects newly introduced bills touching STR rules
- Fires alerts for any new STR-related legislation

New Orleans has active STR regulation: density caps by neighborhood,
residential vs commercial permit tiers, and ongoing enforcement changes.
"""

from typing import Any, List, Optional
import logging
import requests
from datetime import datetime, timezone, timedelta

from scrapers.keywords import matches_keywords
from db import store
from alerts import notify

log = logging.getLogger(__name__)

BASE = "https://webapi.legistar.com/v1/cityofno"
CITY = "New Orleans, LA"


def _get(path: str, params: dict = None) -> Optional[Any]:
    url = f"{BASE}{path}"
    headers = {"Accept": "application/json"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=20)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        log.error("NOLA Legistar HTTP error %s: %s", url, e)
    except Exception as e:
        log.error("NOLA Legistar request error %s: %s", url, e)
    return None


def fetch_recent_legislation(days_back: int = 14) -> List[dict]:
    """
    Fetch legislation introduced in the last N days.
    Uses Legistar REST API /Matters endpoint with OData filter.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00")

    params = {
        "$filter": f"MatterIntroDate ge datetime'{cutoff}'",
        "$orderby": "MatterIntroDate desc",
        "$top": 200,
    }

    log.debug("Fetching NOLA legislation since %s", cutoff)
    results = _get("/Matters", params=params)
    if not results:
        return []

    log.info("NOLA Legistar: %d items in last %d days", len(results), days_back)
    return results


def fetch_legislation_text(matter_id: int) -> str:
    """Fetch full text of a matter for keyword scanning."""
    files = _get(f"/Matters/{matter_id}/MatterTexts")
    if not files:
        return ""
    texts = []
    for f in files:
        t = f.get("MatterTextPlain") or f.get("MatterTextRtf") or ""
        texts.append(t)
    return " ".join(texts)


def get_matter_url(matter_id: int) -> str:
    return f"https://cityofno.legistar.com/LegislationDetail.aspx?ID={matter_id}&GUID=&Search="


def run(days_back: int = 14):
    """
    Main entry point. Fetch recent NOLA legislation, filter for STR keywords,
    save new items, and fire alerts.
    """
    log.info("=== New Orleans Legistar scraper (last %d days) ===", days_back)

    matters = fetch_recent_legislation(days_back=days_back)
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
        url = get_matter_url(matter_id)

        # Quick title scan first (fast) — uses shared word-boundary matching
        title_matches = matches_keywords(title)

        # If title matches, also scan full text for more context
        body_matches = []
        if title_matches or any(kw.lower() in matter_type.lower() for kw in ["rental", "str", "lodging", "airbnb"]):
            try:
                text = fetch_legislation_text(matter_id)
                body_matches = matches_keywords(text)
            except Exception as e:
                errors += 1
                log.warning("Could not fetch text for NOLA matter %s: %s", matter_id, e)

        all_matches = list(set(title_matches + body_matches))
        if not all_matches:
            continue

        total_str_matches += 1
        log.info("STR match: [%s] %s (keywords: %s)", bill_id, title[:80], all_matches[:3])

        try:
            is_new = store.save_legislation(
                city=CITY,
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
                })
        except Exception as e:
            errors += 1
            log.error("DB error for NOLA matter %s: %s", matter_id, e)

    log.info("NOLA Legistar done — checked: %d | STR matches: %d | new: %d | errors: %d",
             checked, total_str_matches, len(new_bills), errors)

    # Alert on each new bill individually
    for bill in new_bills:
        notify.alert_new_legislation(
            city=CITY,
            bill_id=bill["bill_id"],
            title=bill["title"],
            url=bill["url"],
            keywords=bill["keywords"],
        )

    return {
        "checked": checked,
        "str_matches": total_str_matches,
        "new_bills": len(new_bills),
        "errors": errors,
    }


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.DEBUG)
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    result = run(days_back=days)
    print(f"\nResult: {result}")
