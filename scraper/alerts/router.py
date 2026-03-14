"""
alerts/router.py — Alert routing engine.

Queries Supabase user_markets for users watching a city,
looks up their email via Clerk, and sends alert via Resend.
"""

import os
import logging
import requests
from typing import List, Optional
from dotenv import load_dotenv
load_dotenv()

log = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://vnybfdzcwwsluwyznayq.supabase.co")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY", "")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM = os.getenv("RESEND_FROM", "STRWatch <alerts@strwatch.io>")


def get_users_for_city(city: str) -> List[str]:
    if not SUPABASE_SERVICE_KEY:
        log.warning("SUPABASE_SERVICE_ROLE_KEY not set")
        return []
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/user_markets",
        headers={"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"},
        params={"city": f"eq.{city}", "select": "user_id"},
        timeout=10,
    )
    if not resp.ok:
        log.error("Supabase query failed: %s %s", resp.status_code, resp.text)
        return []
    return [row["user_id"] for row in resp.json()]


def get_user_email(user_id: str) -> Optional[str]:
    if not CLERK_SECRET_KEY:
        log.warning("CLERK_SECRET_KEY not set")
        return None
    resp = requests.get(
        f"https://api.clerk.com/v1/users/{user_id}",
        headers={"Authorization": f"Bearer {CLERK_SECRET_KEY}"},
        timeout=10,
    )
    if not resp.ok:
        log.error("Clerk lookup failed for %s: %s", user_id, resp.status_code)
        return None
    data = resp.json()
    emails = data.get("email_addresses", [])
    primary_id = data.get("primary_email_address_id")
    for e in emails:
        if e.get("id") == primary_id:
            return e.get("email_address")
    return emails[0].get("email_address") if emails else None


def send_alert_email(to_email: str, subject: str, city: str,
                     headline: str, detail: str, source_url: str,
                     urgency: str = "medium") -> bool:
    if not RESEND_API_KEY:
        log.warning("RESEND_API_KEY not set — skipping email to %s", to_email)
        return False

    colors = {
        "high":   {"bg": "#fff0ee", "border": "#f7c8c8", "text": "#b84040", "label": "Urgent"},
        "medium": {"bg": "#fdf3e3", "border": "#f5d9a0", "text": "#b87d2d", "label": "Heads up"},
        "low":    {"bg": "#e8f5ee", "border": "#c8ecd8", "text": "#2d7a4f", "label": "FYI"},
    }
    c = colors.get(urgency, colors["medium"])

    html = f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#f7f9f5;font-family:Arial,sans-serif;">
<div style="max-width:560px;margin:40px auto;background:white;border:1.5px solid #d8e8cf;border-radius:12px;overflow:hidden;">
  <div style="background:#1a4d2e;padding:20px 28px;">
    <span style="font-weight:800;font-size:1rem;color:white;">STR<span style="color:#4db87a;">Watch</span></span>
    <span style="margin-left:12px;font-size:0.65rem;letter-spacing:0.15em;text-transform:uppercase;color:rgba(255,255,255,0.5);">Regulation Alert</span>
  </div>
  <div style="padding:16px 28px 0;">
    <span style="display:inline-block;background:{c['bg']};border:1px solid {c['border']};color:{c['text']};font-size:0.7rem;letter-spacing:0.1em;text-transform:uppercase;padding:5px 12px;border-radius:100px;font-weight:600;">{c['label']} · {city}</span>
  </div>
  <div style="padding:16px 28px 12px;">
    <h2 style="margin:0;font-size:1.05rem;font-weight:700;color:#0f1a0a;line-height:1.4;">{headline}</h2>
  </div>
  <div style="margin:0 28px 20px;background:#f7f9f5;border:1px solid #d8e8cf;border-radius:8px;padding:14px 16px;">
    <p style="margin:0;font-size:0.88rem;color:#374530;line-height:1.65;">{detail}</p>
  </div>
  <div style="padding:0 28px 20px;">
    <a href="{source_url}" style="display:inline-block;background:#1a4d2e;color:white;text-decoration:none;font-size:0.8rem;font-weight:700;padding:10px 20px;border-radius:7px;">View source →</a>
  </div>
  <div style="background:#f7f9f5;border-top:1px solid #d8e8cf;padding:14px 28px;">
    <p style="margin:0;font-size:0.7rem;color:#9aab90;">You're receiving this because you're watching <strong>{city}</strong> on STRWatch.<br>
    <a href="https://app.strwatch.io/dashboard/markets" style="color:#2d7a4f;">Manage your markets</a></p>
  </div>
</div></body></html>"""

    text = f"{headline}\n\n{detail}\n\nSource: {source_url}\n\nManage markets: https://app.strwatch.io/dashboard/markets"

    resp = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
        json={"from": RESEND_FROM, "to": [to_email], "subject": f"[STRWatch] {subject}", "html": html, "text": text},
        timeout=15,
    )
    if resp.ok:
        log.info("Alert sent to %s", to_email)
        return True
    log.error("Resend failed for %s: %s %s", to_email, resp.status_code, resp.text)
    return False


def send_city_alert(city: str, subject: str, headline: str,
                    detail: str, source_url: str, urgency: str = "medium") -> dict:
    log.info("Routing alert for city: %s", city)
    user_ids = get_users_for_city(city)
    if not user_ids:
        log.info("No users watching %s", city)
        return {"city": city, "users": 0, "sent": 0, "failed": 0}

    sent = failed = 0
    for user_id in user_ids:
        email = get_user_email(user_id)
        if not email:
            failed += 1
            continue
        ok = send_alert_email(email, subject, city, headline, detail, source_url, urgency)
        if ok: sent += 1
        else: failed += 1

    log.info("Done — city: %s | sent: %d | failed: %d", city, sent, failed)
    return {"city": city, "users": len(user_ids), "sent": sent, "failed": failed}


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.DEBUG)
    city = sys.argv[1] if len(sys.argv) > 1 else "Nashville, TN"
    print(f"Users watching {city}: {get_users_for_city(city)}")
    if "--send" in sys.argv:
        result = send_city_alert(
            city=city,
            subject="Test alert from STRWatch",
            headline="Test alert — your regulation monitoring is working",
            detail="This is a test to confirm alert routing works end to end.",
            source_url="https://app.strwatch.io/dashboard",
            urgency="low",
        )
        print(f"Result: {result}")
