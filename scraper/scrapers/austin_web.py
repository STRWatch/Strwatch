"""
scrapers/austin_web.py — Austin STR page monitoring + council agenda PDF parsing.

Two jobs:
1. Hash-watch austintexas.gov/department/short-term-rentals for any changes
2. Download and keyword-scan council meeting agenda PDFs for STR mentions

Austin has a hard July 1, 2026 deadline (platform enforcement).
This scraper escalates to daily monitoring in the 30-day window before that date.
"""

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
    logging.warning("pdfplumber not installed — PDF parsing disabled. Run: pip install pdfplumber")

import config
from db import store
from alerts import notify

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "STRWatch/1.0 (regulatory monitoring tool; contact@strwatch.io)",
    "Accept": "text/html,application/xhtml+xml,application/xml,application/pdf",
}

STR_PAGE = config.AUSTIN_STR_PAGE
COUNCIL_PAGE = config.AUSTIN_COUNCIL_AGENDA_BASE

# July 1, 2026 enforcement cliff
ENFORCEMENT_DEADLINE = date(2026, 7, 1)
DEADLINE_WARNING_DAYS = 30  # Start daily monitoring this many days before


def _days_to_deadline() -> int:
    return (ENFORCEMENT_DEADLINE - date.today()).days


def _is_deadline_window() -> bool:
    days = _days_to_deadline()
    return 0 <= days <= DEADLINE_WARNING_DAYS


# ── HTML hash watcher ─────────────────────────────────────────────────────────

def _fetch_page_content(url: str) -> Optional[tuple]:
    """Fetch URL, return (hash, content_length) or None on error."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()

        # Parse to extract main content (ignore nav/footer/dynamic timestamps)
        soup = BeautifulSoup(resp.text, "lxml")

        # Remove navigation, footer, scripts, style — we only care about content changes
        for tag in soup(["nav", "footer", "script", "style", "header"]):
            tag.decompose()

        # Extract main content area if possible
        main = soup.find("main") or soup.find(id="content") or soup.find(class_="content") or soup.body
        content = main.get_text(separator=" ", strip=True) if main else resp.text

        content_hash = hashlib.sha256(content.encode()).hexdigest()
        return content_hash, len(content)

    except requests.exceptions.HTTPError as e:
        log.error("HTTP error fetching %s: %s", url, e)
    except Exception as e:
        log.error("Error fetching %s: %s", url, e)
    return None


def watch_page(name: str, url: str, city: str, priority: str = "high") -> bool:
    """
    Check if a page has changed since last snapshot.
    Returns True if a change was detected.
    """
    result = _fetch_page_content(url)
    if result is None:
        log.warning("Could not fetch %s — skipping", url)
        return False

    current_hash, content_len = result
    last = store.get_last_snapshot(url)

    if last is None:
        # First time seeing this page — save baseline, no alert
        store.save_snapshot(url, name, city, current_hash, content_len, changed=False)
        log.info("Baseline saved for: %s", name)
        return False

    if last["hash"] == current_hash:
        store.save_snapshot(url, name, city, current_hash, content_len, changed=False)
        log.debug("No change: %s", name)
        return False

    # Change detected!
    store.save_snapshot(url, name, city, current_hash, content_len, changed=True)
    log.info("CHANGE DETECTED: %s | old_len=%d new_len=%d",
             name, last.get("content_len", 0), content_len)
    notify.alert_page_changed(name, city, url, priority)
    return True


# ── Austin council agenda PDF parser ─────────────────────────────────────────

def _find_agenda_pdf_urls(council_index_url: str) -> List[dict]:
    """
    Scrape the Austin council meetings year-index page to find recent meeting pages,
    then pull agenda PDF links from each meeting page.
    
    Austin's new URL structure (2026+):
      Index: /department/city-council/2026/2026_council_index.htm
      Meeting: /department/city-council/2026/20260312-reg.htm
    
    Returns list of {url, meeting_date, title}.
    """
    try:
        resp = requests.get(council_index_url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        log.error("Could not fetch Austin council index page: %s", e)
        return []

    # Find links to individual meeting pages (e.g. 20260312-reg.htm)
    base = "https://www.austintexas.gov"
    meeting_urls = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # Match year-based meeting URLs like /department/city-council/2026/20260312-reg.htm
        if re.search(r'/city-council/\d{4}/\d{8}-reg\.htm', href):
            full_url = urljoin(base, href)
            if full_url not in meeting_urls:
                meeting_urls.append(full_url)

    log.info("Found %d council meeting pages on Austin index", len(meeting_urls))

    # Visit the 3 most recent meetings and pull PDF links
    agendas = []
    for meeting_url in meeting_urls[:3]:
        try:
            resp = requests.get(meeting_url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            msoup = BeautifulSoup(resp.text, "lxml")
        except Exception as e:
            log.warning("Could not fetch Austin meeting page %s: %s", meeting_url, e)
            continue

        meeting_date = _extract_date_from_url(meeting_url) or "unknown"

        for a in msoup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            text_lower = text.lower()
            href_lower = href.lower()

            is_agenda = "agenda" in text_lower or "agenda" in href_lower
            is_pdf = href_lower.endswith(".pdf") or "pdf" in href_lower

            if is_agenda and is_pdf:
                full_url = urljoin(base, href)
                agendas.append({
                    "url": full_url,
                    "title": text or full_url.split("/")[-1],
                    "meeting_date": meeting_date,
                    "meeting_page": meeting_url,
                })

    log.info("Found %d agenda PDF links across recent Austin meeting pages", len(agendas))
    return agendas[:10]


def _extract_date_from_text(text: str) -> Optional[str]:
    """Try to extract a date string from link text."""
    patterns = [
        r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]* \d{1,2},? \d{4}",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(0)
    return None


def _extract_date_from_url(url: str) -> Optional[str]:
    """Try to extract a date from a URL path."""
    m = re.search(r"(\d{4})[_-]?(\d{2})[_-]?(\d{2})", url)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None


def _keyword_scan_pdf(pdf_url: str) -> List[str]:
    """
    Download and scan a PDF for STR keywords.
    Returns list of matched keywords.
    """
    if not PDF_AVAILABLE:
        return []

    try:
        resp = requests.get(pdf_url, headers=HEADERS, timeout=30, stream=True)
        resp.raise_for_status()

        # Only process if it's actually a PDF
        content_type = resp.headers.get("content-type", "")
        if "pdf" not in content_type and not pdf_url.lower().endswith(".pdf"):
            log.warning("Not a PDF: %s (%s)", pdf_url, content_type)
            return []

        pdf_bytes = io.BytesIO(resp.content)
        full_text = ""
        with pdfplumber.open(pdf_bytes) as pdf:
            for page in pdf.pages[:20]:  # First 20 pages max
                text = page.extract_text()
                if text:
                    full_text += text + " "

        matches = []
        full_lower = full_text.lower()
        for kw in config.STR_KEYWORDS:
            if kw.lower() in full_lower:
                matches.append(kw)

        if matches:
            log.info("PDF keyword match: %s → %s", pdf_url.split("/")[-1], matches[:5])

        return matches

    except Exception as e:
        log.error("PDF scan error %s: %s", pdf_url, e)
        return []


def scan_austin_council_agendas():
    """Download and scan recent Austin council agenda PDFs for STR mentions."""
    log.info("Scanning Austin council agenda PDFs...")

    agendas = _find_agenda_pdf_urls(COUNCIL_PAGE)
    new_bills = []

    for agenda in agendas:
        pdf_url = agenda["url"]
        meeting_date = agenda.get("meeting_date", "unknown")
        title = agenda.get("title", pdf_url.split("/")[-1])

        # Use PDF URL as bill_id for dedup
        keywords = _keyword_scan_pdf(pdf_url)
        if not keywords:
            continue

        # Generate a stable bill_id from the PDF URL
        bill_id = "AGENDA-" + hashlib.md5(pdf_url.encode()).hexdigest()[:8].upper()

        is_new = store.save_legislation(
            city="Austin",
            source="CouncilAgenda",
            bill_id=bill_id,
            title=f"Council Agenda: {title}",
            description=f"STR keywords found in council agenda PDF",
            status="agenda",
            introduced_date=meeting_date,
            url=pdf_url,
            keyword_matches=keywords,
            raw=agenda,
        )

        if is_new:
            new_bills.append({
                "bill_id": bill_id,
                "title": f"Austin Council Agenda ({meeting_date})",
                "url": pdf_url,
                "keywords": keywords,
            })
            log.info("New STR agenda item: %s (keywords: %s)", title, keywords[:3])

    for bill in new_bills:
        notify.alert_new_legislation(
            city="Austin",
            bill_id=bill["bill_id"],
            title=bill["title"],
            url=bill["url"],
            keywords=bill["keywords"],
        )

    return len(new_bills)


def check_deadline_proximity():
    """
    If we're within 30 days of the July 1 enforcement deadline,
    send a reminder alert (once per week).
    """
    days = _days_to_deadline()
    if days < 0:
        log.info("Austin July 1 deadline has passed (%d days ago)", abs(days))
        return

    if not _is_deadline_window():
        return

    # Weekly reminder during the window
    week_num = days // 7
    alert_key = f"austin_deadline_week_{week_num}"

    if not store.already_alerted(alert_key):
        from alerts.notify import send_email, send_sms
        from db.store import record_alert

        subject = f"[STRWatch] ⚠️ Austin July 1 deadline: {days} days remaining"
        html = f"""
        <div style="font-family:monospace;max-width:600px;padding:24px;">
          <div style="background:#e8b84b;color:#1a1612;padding:12px 16px;font-size:12px;letter-spacing:2px;text-transform:uppercase;font-weight:bold;">
            STRWatch · Austin Deadline Reminder
          </div>
          <div style="border:2px solid #e8b84b;padding:20px;">
            <p style="font-size:24px;font-weight:bold;color:#1a1612;margin:0 0 8px;">
              {days} days until July 1, 2026
            </p>
            <p style="color:#3d3530;font-size:14px;margin:0 0 16px;">
              On July 1, 2026, Austin begins requesting removal of unlicensed STRs from all platforms
              (Airbnb, VRBO, etc.). Any host without an active license will be delisted.
            </p>
            <p style="color:#8a7f74;font-size:13px;margin:0;">
              Source: <a href="{STR_PAGE}" style="color:#2d5a8e;">austintexas.gov/department/short-term-rentals</a>
            </p>
          </div>
        </div>
        """
        text = f"[STRWatch] Austin July 1 deadline: {days} days remaining. Unlicensed STRs will be removed from platforms. Check: {STR_PAGE}"
        sms = f"[STRWatch] Austin enforcement deadline: {days} days left. Unlicensed STRs removed July 1."

        send_email(subject, html, text)
        send_sms(sms)
        record_alert(alert_key, "deadline_reminder", "Austin", f"{days} days to July 1 deadline")
        log.info("Austin deadline reminder sent: %d days remaining", days)


# ── Main run function ─────────────────────────────────────────────────────────

def run():
    """Main entry point for Austin scraper."""
    log.info("=== Austin scraper starting ===")

    changes = 0
    new_agenda_items = 0

    # 1. Watch key pages
    for page in config.WATCHED_PAGES:
        if page["city"] != "Austin":
            continue
        changed = watch_page(page["name"], page["url"], page["city"], page["priority"])
        if changed:
            changes += 1

    # 2. Scan council agendas for STR mentions
    try:
        new_agenda_items = scan_austin_council_agendas()
    except Exception as e:
        log.error("Austin agenda scan failed: %s", e)

    # 3. Check deadline proximity
    check_deadline_proximity()

    log.info("Austin scraper done — page changes: %d | new agenda items: %d | deadline: %d days",
             changes, new_agenda_items, _days_to_deadline())

    return {
        "page_changes": changes,
        "new_agenda_items": new_agenda_items,
        "days_to_deadline": _days_to_deadline(),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    result = run()
    print(f"\nResult: {result}")
