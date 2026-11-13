"""
alerts/digest.py — Weekly digest for Free-tier users.

router.send_city_alert() inserts an `alerts` row with sent_at NULL for any
watching user whose effective tier is not pro/agency (free, or expired
trial). This module sends each such user ONE email listing every pending
alert grouped by city, then stamps sent_at on those rows.

Run from the scraper directory (plain load_dotenv() needs the cwd):

    cd /root/strwatch-scraper && /usr/bin/python3 -m alerts.digest
    cd /root/strwatch-scraper && /usr/bin/python3 -m alerts.digest --dry-run

Cron (Sunday 14:00 UTC):
    0 14 * * 0 cd /root/strwatch-scraper && /usr/bin/python3 -m alerts.digest >> /var/log/strwatch-digest.log 2>&1
"""

import logging
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests

from alerts import router
from alerts.router import esc, source_link_html

log = logging.getLogger(__name__)

URGENCY_LABEL = {"high": "Urgent", "medium": "Heads up", "low": "FYI"}
URGENCY_COLOR = {"high": "#b84040", "medium": "#b87d2d", "low": "#2d7a4f"}


def _headers() -> dict:
    return {
        "apikey": router.SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {router.SUPABASE_SERVICE_KEY}",
    }


def fetch_pending_alerts() -> List[dict]:
    """All alerts rows with sent_at IS NULL, oldest first."""
    if not router.SUPABASE_SERVICE_KEY:
        log.warning("SUPABASE_SERVICE_ROLE_KEY not set — nothing to do")
        return []
    resp = requests.get(
        f"{router.SUPABASE_URL}/rest/v1/alerts",
        headers=_headers(),
        params={
            "sent_at": "is.null",
            "select": "id,user_id,city,subject,headline,detail,source_url,urgency",
            "order": "id.asc",
        },
        timeout=15,
    )
    if not resp.ok:
        log.error("Failed to fetch pending alerts: %s %s", resp.status_code, resp.text)
        return []
    return resp.json()


def group_alerts(rows: List[dict]) -> "OrderedDict[str, OrderedDict[str, List[dict]]]":
    """{user_id: {city: [alert, ...]}} preserving input order."""
    by_user: "OrderedDict[str, OrderedDict[str, List[dict]]]" = OrderedDict()
    for row in rows:
        user_id = row.get("user_id")
        if not user_id:
            continue
        city = row.get("city") or "Other"
        by_user.setdefault(user_id, OrderedDict()).setdefault(city, []).append(row)
    return by_user


def build_digest_email(by_city: "OrderedDict[str, List[dict]]") -> dict:
    """Return {"subject", "html", "text"} for one user's digest.

    Every value from the alerts table is escaped; source_url only becomes an
    href when it is https://.
    """
    total = sum(len(v) for v in by_city.values())
    cities = list(by_city.keys())
    subject = f"[STRWatch] Weekly digest — {total} update{'s' if total != 1 else ''} in {len(cities)} market{'s' if len(cities) != 1 else ''}"

    sections_html = []
    text_lines = [f"STRWatch weekly digest — {total} update(s)", ""]
    for city, alerts in by_city.items():
        city_e = esc(city)
        items_html = []
        text_lines.append(f"== {city} ==")
        for a in alerts:
            urgency = (a.get("urgency") or "medium").lower()
            label = URGENCY_LABEL.get(urgency, "Heads up")
            color = URGENCY_COLOR.get(urgency, URGENCY_COLOR["medium"])
            link = source_link_html(
                a.get("source_url"), label="View source →",
                style="font-size:0.8rem;color:#2d7a4f;font-weight:600;text-decoration:none;",
            )
            items_html.append(f"""
      <div style="padding:12px 0;border-top:1px solid #e6eee0;">
        <div style="font-size:0.65rem;letter-spacing:0.1em;text-transform:uppercase;color:{color};font-weight:700;">{label}</div>
        <div style="font-size:0.95rem;font-weight:700;color:#0f1a0a;margin:4px 0;">{esc(a.get('headline'))}</div>
        <div style="font-size:0.85rem;color:#374530;line-height:1.55;">{esc(a.get('detail'))}</div>
        <div style="margin-top:6px;">{link}</div>
      </div>""")
            text_lines.append(f"- [{label}] {a.get('headline') or ''}")
            if a.get("detail"):
                text_lines.append(f"  {a.get('detail')}")
            if a.get("source_url"):
                text_lines.append(f"  Source: {a.get('source_url')}")
        text_lines.append("")
        sections_html.append(f"""
    <div style="padding:16px 28px 4px;">
      <h3 style="margin:0 0 4px;font-size:1rem;color:#1a4d2e;">{city_e} <span style="font-weight:400;color:#9aab90;">· {len(alerts)}</span></h3>
      {''.join(items_html)}
    </div>""")

    html = f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#f7f9f5;font-family:Arial,sans-serif;">
<div style="max-width:560px;margin:40px auto;background:white;border:1.5px solid #d8e8cf;border-radius:12px;overflow:hidden;">
  <div style="background:#1a4d2e;padding:20px 28px;">
    <span style="font-weight:800;font-size:1rem;color:white;">STR<span style="color:#4db87a;">Watch</span></span>
    <span style="margin-left:12px;font-size:0.65rem;letter-spacing:0.15em;text-transform:uppercase;color:rgba(255,255,255,0.5);">Weekly Digest</span>
  </div>
  <div style="padding:16px 28px 0;">
    <p style="margin:0;font-size:0.88rem;color:#374530;">{total} regulation update{'s' if total != 1 else ''} across the markets you watch this week.</p>
  </div>
  {''.join(sections_html)}
  <div style="padding:16px 28px 20px;">
    <a href="https://app.strwatch.io/dashboard/settings" style="display:inline-block;background:#1a4d2e;color:white;text-decoration:none;font-size:0.8rem;font-weight:700;padding:10px 20px;border-radius:7px;">Upgrade for real-time alerts →</a>
  </div>
  <div style="background:#f7f9f5;border-top:1px solid #d8e8cf;padding:14px 28px;">
    <p style="margin:0;font-size:0.7rem;color:#9aab90;">Free plans receive a weekly digest. <a href="https://app.strwatch.io/dashboard/settings" style="color:#2d7a4f;">Manage notifications</a></p>
  </div>
</div></body></html>"""

    text_lines.append("Manage notifications: https://app.strwatch.io/dashboard/settings")
    return {"subject": subject, "html": html, "text": "\n".join(text_lines)}


def send_digest_email(to_email: str, email: dict) -> bool:
    if not router.RESEND_API_KEY:
        log.warning("RESEND_API_KEY not set — skipping digest to %s", to_email)
        return False
    resp = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {router.RESEND_API_KEY}", "Content-Type": "application/json"},
        json={"from": router.RESEND_FROM, "to": [to_email], "subject": email["subject"],
              "html": email["html"], "text": email["text"]},
        timeout=15,
    )
    if resp.ok:
        log.info("Digest email sent to %s", to_email)
        return True
    log.error("Resend failed for %s: %s %s", to_email, resp.status_code, resp.text)
    return False


def mark_sent(alert_ids: List) -> bool:
    """Set sent_at = now() on the given alerts rows."""
    if not alert_ids:
        return True
    id_list = ",".join(str(i) for i in alert_ids)
    resp = requests.patch(
        f"{router.SUPABASE_URL}/rest/v1/alerts",
        headers={**_headers(), "Content-Type": "application/json", "Prefer": "return=minimal"},
        params={"id": f"in.({id_list})"},
        json={"sent_at": datetime.now(timezone.utc).isoformat()},
        timeout=15,
    )
    if not resp.ok:
        log.error("Failed to mark alerts sent: %s %s", resp.status_code, resp.text)
        return False
    return True


def run(dry_run: bool = False) -> dict:
    """Send one digest per user with pending (sent_at NULL) alerts."""
    rows = fetch_pending_alerts()
    by_user = group_alerts(rows)
    log.info("Digest: %d pending alert(s) for %d user(s)%s",
             len(rows), len(by_user), " [DRY RUN]" if dry_run else "")

    users = sent = failed = marked = 0
    for user_id, by_city in by_user.items():
        users += 1
        ids = [a["id"] for cities in by_city.values() for a in cities if a.get("id") is not None]
        email_addr = router.get_user_email(user_id)
        email = build_digest_email(by_city)

        if dry_run:
            log.info("DRY RUN: would send to %s (%s): %s — %d alert(s) in %s",
                     user_id, email_addr or "no email", email["subject"], len(ids), list(by_city.keys()))
            continue

        if not email_addr:
            log.warning("No email for user %s — leaving %d alert(s) pending", user_id, len(ids))
            failed += 1
            continue

        if send_digest_email(email_addr, email):
            sent += 1
            if mark_sent(ids):
                marked += len(ids)
        else:
            failed += 1

    result = {"pending": len(rows), "users": users, "sent": sent, "failed": failed,
              "marked": marked, "dry_run": dry_run}
    log.info("Digest done: %s", result)
    return result


def main(argv: Optional[List[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    logging.basicConfig(
        level=logging.DEBUG if "--debug" in argv else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    result = run(dry_run="--dry-run" in argv)
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
