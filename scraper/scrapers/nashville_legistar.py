"""
scrapers/nashville_legistar.py — Nashville Metro Council legislation via Legistar API.

Nashville uses Legistar (webapi.legistar.com/v1/nashville).
- Searches for STR-related legislation by keyword
- Detects newly introduced bills touching STR rules
- Fires alerts for any new STR-related legislation
"""

from typing import Any, List, Optional
import logging
import requests
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

import config
from db import store
from alerts import notify

log = logging.getLogger(__name__)

BASE = config.NASHVILLE_LEGISTAR_BASE
KEYWORDS = config.STR_KEYWORDS


def _get(path: str, params: dict = None) -> Optional[Any]:
    url = f"{BASE}{path}"
    try:
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        log.error("Legistar HTTP error %s: %s", url, e)
    except Exception as e:
        log.error("Legistar request error %s: %s", url, e)
    return None


def _matches_keywords(text: str) -> List[str]:
    """Return list of STR keywords found in text (case-insensitive)."""
    if not text:
        return []
    import re
    matches = []
    text_lower = text.lower()
    for kw in KEYWORDS:
        pattern = r"" + re.escape(kw.lower()) + r""
        if re.search(pattern, text_lower):
            matches.append(kw)
    return matches


def fetch_recent_legislation(days_back: int = 14) -> List[dict]:
    """
    Fetch legislation introduced in the last N days.
    Uses Legistar REST API /Legislation endpoint.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00")

    # Legistar OData filter
    params = {
        "$filter": f"MatterIntroDate ge datetime'{cutoff}'",
        "$orderby": "MatterIntroDate desc",
        "$top": 200,
    }

    log.debug("Fetching Nashville legislation since %s", cutoff)
    results = _get("/Matters", params=params)
    if not results:
        return []

    log.info("Nashville Legistar: %d items in last %d days", len(results), days_back)
    return results


def fetch_legislation_text(matter_id: int) -> str:
    """Fetch full text of a matter for keyword scanning."""
    files = _get(f"/Matters/{matter_id}/MatterTexts")
    if not files:
        return ""
    # Return concatenated text from all versions
    texts = []
    for f in files:
        t = f.get("MatterTextPlain") or f.get("MatterTextRtf") or ""
        texts.append(t)
    return " ".join(texts)


def get_matter_url(matter_id: int) -> str:
    return f"https://nashville.legistar.com/LegislationDetail.aspx?ID={matter_id}&GUID=&Search="


def run(days_back: int = 14):
    """
    Main entry point. Fetch recent Nashville legislation, filter for STR keywords,
    save new items, and fire alerts.
    """
    log.info("=== Nashville Legistar scraper (last %d days) ===", days_back)

    matters = fetch_recent_legislation(days_back=days_back)
    new_bills = []
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

        # Quick title scan first (fast)
        title_matches = _matches_keywords(title)

        # If title matches, also scan full text
        body_matches = []
        if title_matches or any(kw.lower() in matter_type.lower() for kw in ["rental", "str"]):
            try:
                text = fetch_legislation_text(matter_id)
                body_matches = _matches_keywords(text)
            except Exception as e:
                errors += 1
                log.warning("Could not fetch text for matter %s: %s", matter_id, e)

        all_matches = list(set(title_matches + body_matches))
        if not all_matches:
            continue

        log.info("STR match: [%s] %s (keywords: %s)", bill_id, title[:80], all_matches[:3])

        try:
            is_new = store.save_legislation(
                city="Nashville",
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
            log.error("DB error for matter %s: %s", matter_id, e)

    log.info("Nashville Legistar done — checked: %d | STR matches: %d | new: %d | errors: %d",
             checked, len(new_bills) + (checked - checked),  # checked all
             len(new_bills), errors)

    # Alert on each new bill individually
    for bill in new_bills:
        notify.alert_new_legislation(
            city="Nashville",
            bill_id=bill["bill_id"],
            title=bill["title"],
            url=bill["url"],
            keywords=bill["keywords"],
        )

    return {
        "checked": checked,
        "new_bills": len(new_bills),
        "errors": errors,
    }


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.DEBUG)
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    result = run(days_back=days)
    print(f"\nResult: {result}")
