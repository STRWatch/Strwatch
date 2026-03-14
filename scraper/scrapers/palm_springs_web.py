"""
scrapers/palm_springs_web.py — Palm Springs STR page monitoring.

Palm Springs has no public license database API.
Instead we watch the key city pages for changes and scan
council agenda PDFs for STR-related ordinance activity.

Key facts about Palm Springs STR regulation:
- One of the strictest regimes in the US
- 20% neighborhood density cap (10 of 66 neighborhoods already at cap)
- 26 rental contracts/year max (reduced from 36 as of Jan 1, 2026)
- $1,072/yr registration fee per property
- $5,000 fines + permanent disqualification for violations
- TOT: 11.5% + city tax = ~19.75% total tax burden
- City publicly lists suspended properties

Key pages watched:
- Vacation Rentals hub (regulation changes, new ordinances)
- Vacation Rental Density page (neighborhood cap updates — high value)
- Department Reports page (enforcement data)
- City Council agendas (ordinance changes)
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import hashlib
import re
import requests
import io
from datetime import datetime, timezone, date
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from typing import List, Optional

try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logging.warning("pdfplumber not installed — PDF parsing disabled.")

import config
from db import store
from alerts import notify

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.google.com/",
}

# Key pages to watch
WATCHED_PAGES = [
    {
        "name": "Palm Springs PrimeGov Council Portal",
        "url": "https://palmsprings.primegov.com/public/portal",
        "priority": "high",
    },

]

# Palm Springs city council uses Legistar
LEGISTAR_BASE = "https://webapi.legistar.com/v1/palmsprings"

STR_KEYWORDS = config.STR_KEYWORDS


# ── HTML hash watcher ─────────────────────────────────────────────────────────

def _fetch_page_content(url: str) -> Optional[tuple]:
    """Fetch URL, return (hash, content_length) or None on error."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["nav", "footer", "script", "style", "header"]):
            tag.decompose()
        main = soup.find("main") or soup.find(id="content") or soup.find(class_="content") or soup.body
        content = main.get_text(separator=" ", strip=True) if main else resp.text
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        return content_hash, len(content)
    except Exception as e:
        log.error("Error fetching %s: %s", url, e)
    return None


def watch_page(name: str, url: str, priority: str = "high") -> bool:
    """Check if a page has changed. Returns True if changed."""
    result = _fetch_page_content(url)
    if result is None:
        log.warning("Could not fetch %s — skipping", url)
        return False

    current_hash, content_len = result
    last = store.get_last_snapshot(url)

    if last is None:
        store.save_snapshot(url, name, "Palm Springs", current_hash, content_len, changed=False)
        log.info("Baseline saved for: %s", name)
        return False

    if last["hash"] == current_hash:
        store.save_snapshot(url, name, "Palm Springs", current_hash, content_len, changed=False)
        log.debug("No change: %s", name)
        return False

    store.save_snapshot(url, name, "Palm Springs", current_hash, content_len, changed=True)
    log.info("CHANGE DETECTED: %s | old_len=%d new_len=%d",
             name, last.get("content_len", 0), content_len)
    notify.alert_page_changed(name, "Palm Springs", url, priority)
    return True


# ── Legistar legislation scraper ──────────────────────────────────────────────

def _legistar_get(path: str, params: dict = None):
    """Call Palm Springs Legistar API."""
    url = f"{LEGISTAR_BASE}{path}"
    try:
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        log.warning("Palm Springs Legistar error %s: %s", url, e)
    return None


def _matches_keywords(text: str) -> List[str]:
    """Whole-word keyword matching."""
    if not text:
        return []
    matches = []
    text_lower = text.lower()
    for kw in STR_KEYWORDS:
        pattern = r'\b' + re.escape(kw.lower()) + r'\b'
        if re.search(pattern, text_lower):
            matches.append(kw)
    return matches


def scan_legistar(days_back: int = 14) -> int:
    """Scan Palm Springs Legistar for recent STR-related legislation."""
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00")
    params = {
        "$filter": f"MatterIntroDate ge datetime'{cutoff}'",
        "$orderby": "MatterIntroDate desc",
        "$top": 200,
    }
    matters = _legistar_get("/Matters", params=params)
    if not matters:
        log.info("Palm Springs Legistar: no data (may not be on Legistar)")
        return 0

    log.info("Palm Springs Legistar: %d items in last %d days", len(matters), days_back)
    new_bills = []

    for matter in matters:
        matter_id = matter.get("MatterId")
        title = matter.get("MatterName") or matter.get("MatterTitle") or ""
        status = matter.get("MatterStatusName") or ""
        intro_date = matter.get("MatterIntroDate") or ""
        bill_id = matter.get("MatterFile") or str(matter_id)
        url = f"https://palmsprings.legistar.com/LegislationDetail.aspx?ID={matter_id}&GUID=&Search="

        matches = _matches_keywords(title)
        if not matches:
            continue

        log.info("PS STR match: [%s] %s (keywords: %s)", bill_id, title[:80], matches[:3])

        try:
            is_new = store.save_legislation(
                city="Palm Springs",
                source="Legistar",
                bill_id=str(bill_id),
                title=title,
                description=matter.get("MatterTypeName") or "",
                status=status,
                introduced_date=intro_date[:10] if intro_date else "",
                url=url,
                keyword_matches=matches,
                raw=matter,
            )
            if is_new:
                new_bills.append({"bill_id": bill_id, "title": title,
                                  "url": url, "keywords": matches})
        except Exception as e:
            log.error("DB error for PS matter %s: %s", matter_id, e)

    for bill in new_bills:
        notify.alert_new_legislation(
            city="Palm Springs",
            bill_id=bill["bill_id"],
            title=bill["title"],
            url=bill["url"],
            keywords=bill["keywords"],
        )

    return len(new_bills)


# ── Main run function ─────────────────────────────────────────────────────────

def run():
    """Main entry point for Palm Springs scraper."""
    log.info("=== Palm Springs scraper starting ===")

    page_changes = 0
    new_legislation = 0

    # 1. Watch all key pages
    for page in WATCHED_PAGES:
        try:
            changed = watch_page(page["name"], page["url"], page["priority"])
            if changed:
                page_changes += 1
        except Exception as e:
            log.error("Error watching %s: %s", page["name"], e)

    # 2. Try Legistar (may not be available for Palm Springs)
    try:
        new_legislation = scan_legistar()
    except Exception as e:
        log.warning("Palm Springs Legistar scan failed: %s", e)

    log.info("Palm Springs scraper done — page changes: %d | new legislation: %d",
             page_changes, new_legislation)

    return {
        "page_changes": page_changes,
        "new_legislation": new_legislation,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    result = run()
    print(f"\nResult: {result}")
