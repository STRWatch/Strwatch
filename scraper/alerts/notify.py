"""
alerts/notify.py — Send email (Resend) and SMS (Twilio) alerts.

Includes dedup: won't send the same alert_key twice.
"""

from typing import List
import logging
import hashlib
from datetime import datetime

import config
from db import store

log = logging.getLogger(__name__)


def _make_key(*parts) -> str:
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def send_email(subject: str, body_html: str, body_text: str) -> bool:
    """Send via Resend. Returns True on success."""
    if not config.RESEND_API_KEY or not config.ALERT_EMAIL:
        log.warning("Email not configured — skipping (set RESEND_API_KEY and ALERT_EMAIL in .env)")
        return False
    try:
        import resend
        resend.api_key = config.RESEND_API_KEY
        resend.Emails.send({
            "from": config.RESEND_FROM,
            "to": config.ALERT_EMAIL,
            "subject": subject,
            "html": body_html,
            "text": body_text,
        })
        log.info("Email sent: %s", subject)
        return True
    except Exception as e:
        log.error("Email send failed: %s", e)
        return False


def send_sms(message: str) -> bool:
    """Send via Twilio. Returns True on success."""
    if not all([config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN,
                config.TWILIO_FROM, config.ALERT_PHONE]):
        log.warning("SMS not configured — skipping (set TWILIO_* vars in .env)")
        return False
    try:
        from twilio.rest import Client
        client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=message[:1600],  # Twilio limit
            from_=config.TWILIO_FROM,
            to=config.ALERT_PHONE,
        )
        log.info("SMS sent: %s", message[:60])
        return True
    except Exception as e:
        log.error("SMS send failed: %s", e)
        return False


# ── Alert builders ────────────────────────────────────────────────────────────

def alert_page_changed(name: str, city: str, url: str, priority: str):
    key = _make_key("page_changed", url, datetime.utcnow().strftime("%Y-%m-%d"))
    if store.already_alerted(key):
        return

    subject = f"[STRWatch] {city} regulation page changed — {name}"
    urgency = "🚨 HIGH PRIORITY" if priority == "high" else "ℹ️"

    html = f"""
    <div style="font-family:monospace;max-width:600px;padding:24px;">
      <div style="background:#1a1612;color:#e8b84b;padding:12px 16px;font-size:12px;letter-spacing:2px;text-transform:uppercase;margin-bottom:0;">
        STRWatch Alert
      </div>
      <div style="border:2px solid #c8411a;padding:20px;margin-bottom:0;">
        <p style="margin:0 0 8px;font-size:18px;font-weight:bold;color:#1a1612;">{urgency} {name}</p>
        <p style="margin:0 0 16px;color:#8a7f74;font-size:13px;">City: {city}</p>
        <p style="margin:0 0 8px;color:#3d3530;">A government STR page has changed. Review immediately for new rules, deadlines, or permit requirements.</p>
        <p style="margin:16px 0 0;">
          <a href="{url}" style="background:#c8411a;color:white;padding:10px 20px;text-decoration:none;font-size:12px;letter-spacing:1px;text-transform:uppercase;">
            View Changed Page →
          </a>
        </p>
      </div>
      <p style="font-size:11px;color:#b8ad9e;margin-top:12px;">STRWatch · Detected {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
    </div>
    """

    text = f"[STRWatch] {city} STR page changed: {name}\n\nReview: {url}\n\nDetected: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    sms = f"[STRWatch] {city}: STR regulation page changed — {name}. Check: {url}"

    send_email(subject, html, text)
    if priority == "high":
        send_sms(sms)

    store.record_alert(key, "page_changed", city, f"{name} changed")
    log.info("Alert sent: page_changed for %s", name)
    route_page_change_alert(city, name, url, priority)


def alert_denver_new_licenses(new_records: List[dict]):
    if not new_records:
        return
    key = _make_key("denver_new_licenses", datetime.utcnow().strftime("%Y-%m-%d"), len(new_records))
    if store.already_alerted(key):
        return

    count = len(new_records)
    subject = f"[STRWatch] Denver: {count} new STR license{'s' if count > 1 else ''} issued"

    rows_html = "".join(f"""
        <tr style="border-bottom:1px solid #ddd6c8;">
          <td style="padding:8px 12px;font-size:13px;">{r.get('address','—')}</td>
          <td style="padding:8px 12px;font-size:13px;color:#8a7f74;">{r.get('license_type','—')}</td>
          <td style="padding:8px 12px;font-size:13px;">{r.get('issued_date','—')}</td>
          <td style="padding:8px 12px;font-size:13px;color:#4a7c59;font-weight:bold;">{r.get('status','—')}</td>
        </tr>
    """ for r in new_records[:20])

    html = f"""
    <div style="font-family:monospace;max-width:700px;padding:24px;">
      <div style="background:#1a1612;color:#e8b84b;padding:12px 16px;font-size:12px;letter-spacing:2px;text-transform:uppercase;">
        STRWatch · Denver License Update
      </div>
      <div style="border:1px solid #ddd6c8;padding:20px;">
        <p style="font-size:18px;font-weight:bold;color:#1a1612;margin:0 0 16px;">
          {count} new STR license{'s' if count > 1 else ''} issued in Denver
        </p>
        <table style="width:100%;border-collapse:collapse;">
          <thead>
            <tr style="background:#f5f0e8;">
              <th style="padding:8px 12px;text-align:left;font-size:11px;letter-spacing:1px;text-transform:uppercase;color:#8a7f74;">Address</th>
              <th style="padding:8px 12px;text-align:left;font-size:11px;letter-spacing:1px;text-transform:uppercase;color:#8a7f74;">Type</th>
              <th style="padding:8px 12px;text-align:left;font-size:11px;letter-spacing:1px;text-transform:uppercase;color:#8a7f74;">Issued</th>
              <th style="padding:8px 12px;text-align:left;font-size:11px;letter-spacing:1px;text-transform:uppercase;color:#8a7f74;">Status</th>
            </tr>
          </thead>
          <tbody>{rows_html}</tbody>
        </table>
        {"<p style='color:#8a7f74;font-size:12px;margin-top:12px;'>+ " + str(count - 20) + " more not shown</p>" if count > 20 else ""}
      </div>
      <p style="font-size:11px;color:#b8ad9e;margin-top:12px;">STRWatch · {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
    </div>
    """

    text = f"[STRWatch] Denver: {count} new STR license(s) issued.\n\n" + \
           "\n".join(f"- {r.get('address','?')} ({r.get('status','?')})" for r in new_records[:10])

    send_email(subject, html, text)
    store.record_alert(key, "denver_new_licenses", "Denver", f"{count} new licenses")


def alert_denver_revocations(revoked_records: List[dict]):
    if not revoked_records:
        return
    key = _make_key("denver_revoked", datetime.utcnow().strftime("%Y-%m-%d"), len(revoked_records))
    if store.already_alerted(key):
        return

    count = len(revoked_records)
    subject = f"[STRWatch] 🚨 Denver: {count} STR license{'s' if count > 1 else ''} revoked/expired"

    rows_html = "".join(f"""
        <tr style="border-bottom:1px solid #ddd6c8;">
          <td style="padding:8px 12px;font-size:13px;">{r.get('address','—')}</td>
          <td style="padding:8px 12px;font-size:13px;color:#c8411a;font-weight:bold;">{r.get('status','—')}</td>
          <td style="padding:8px 12px;font-size:13px;color:#8a7f74;">{r.get('expiry_date','—')}</td>
        </tr>
    """ for r in revoked_records[:20])

    html = f"""
    <div style="font-family:monospace;max-width:700px;padding:24px;">
      <div style="background:#c8411a;color:white;padding:12px 16px;font-size:12px;letter-spacing:2px;text-transform:uppercase;">
        STRWatch · Denver Enforcement Alert
      </div>
      <div style="border:2px solid #c8411a;padding:20px;">
        <p style="font-size:18px;font-weight:bold;color:#1a1612;margin:0 0 8px;">
          {count} STR license{'s' if count > 1 else ''} revoked or expired in Denver
        </p>
        <p style="color:#8a7f74;font-size:13px;margin:0 0 16px;">
          Enforcement activity detected. Review affected addresses.
        </p>
        <table style="width:100%;border-collapse:collapse;">
          <thead>
            <tr style="background:#fde8e2;">
              <th style="padding:8px 12px;text-align:left;font-size:11px;letter-spacing:1px;text-transform:uppercase;color:#8a7f74;">Address</th>
              <th style="padding:8px 12px;text-align:left;font-size:11px;letter-spacing:1px;text-transform:uppercase;color:#8a7f74;">New Status</th>
              <th style="padding:8px 12px;text-align:left;font-size:11px;letter-spacing:1px;text-transform:uppercase;color:#8a7f74;">Expiry Date</th>
            </tr>
          </thead>
          <tbody>{rows_html}</tbody>
        </table>
      </div>
      <p style="font-size:11px;color:#b8ad9e;margin-top:12px;">STRWatch · {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
    </div>
    """

    text = f"[STRWatch] ALERT: Denver — {count} STR license(s) revoked/expired.\n\n" + \
           "\n".join(f"- {r.get('address','?')}: {r.get('status','?')}" for r in revoked_records[:10])
    sms = f"[STRWatch] 🚨 Denver: {count} STR license(s) revoked/expired. Check email for details."

    send_email(subject, html, text)
    send_sms(sms)
    store.record_alert(key, "denver_revocations", "Denver", f"{count} revocations")


def alert_new_legislation(city: str, bill_id: str, title: str, url: str, keywords: List[str]):
    key = _make_key("legislation", city, bill_id)
    if store.already_alerted(key):
        return

    kw_str = ", ".join(keywords[:5])
    subject = f"[STRWatch] {city}: New STR legislation — {bill_id}"

    html = f"""
    <div style="font-family:monospace;max-width:600px;padding:24px;">
      <div style="background:#2d5a8e;color:white;padding:12px 16px;font-size:12px;letter-spacing:2px;text-transform:uppercase;">
        STRWatch · New Legislation Detected
      </div>
      <div style="border:2px solid #2d5a8e;padding:20px;">
        <p style="margin:0 0 4px;font-size:12px;color:#8a7f74;text-transform:uppercase;letter-spacing:1px;">
          {city} · {bill_id}
        </p>
        <p style="margin:0 0 12px;font-size:18px;font-weight:bold;color:#1a1612;">{title}</p>
        <p style="margin:0 0 12px;font-size:13px;color:#3d3530;">
          Keywords matched: <strong>{kw_str}</strong>
        </p>
        <p style="margin:16px 0 0;">
          <a href="{url}" style="background:#2d5a8e;color:white;padding:10px 20px;text-decoration:none;font-size:12px;letter-spacing:1px;text-transform:uppercase;">
            View Legislation →
          </a>
        </p>
      </div>
      <p style="font-size:11px;color:#b8ad9e;margin-top:12px;">STRWatch · {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
    </div>
    """

    text = f"[STRWatch] {city}: New STR-related legislation\n\nBill: {bill_id}\nTitle: {title}\nKeywords: {kw_str}\n\nView: {url}"
    sms = f"[STRWatch] {city}: New STR bill — {bill_id}: {title[:80]}. View: {url}"

    send_email(subject, html, text)
    send_sms(sms)
    store.record_alert(key, "legislation", city, f"{bill_id}: {title}")
    log.info("Alert sent: new legislation %s %s", city, bill_id)
    route_legislation_alert(city, title, url, keywords)


def alert_austin_new_licenses(licenses: list):
    if not licenses: return
    count = len(licenses)
    by_type = {}
    for l in licenses:
        t = l.get("license_type") or "Unknown"
        by_type[t] = by_type.get(t, 0) + 1
    summary = ", ".join(f"{n} {t}" for t, n in by_type.items())
    subject = f"[STRWatch] Austin: {count} new STR license(s) — {summary}"
    text = f"{count} new Austin STR license(s): {summary}"
    send_email(subject, f"<p>{text}</p>", text)


def alert_austin_revocations(licenses: list):
    if not licenses: return
    count = len(licenses)
    subject = f"[STRWatch] Austin: {count} STR license revocation(s) detected"
    text = f"ALERT: {count} Austin STR license(s) revoked. July 1 deadline — hosts must reapply."
    send_email(subject, f"<p>{text}</p>", text)
    send_sms(f"[STRWatch] Austin: {count} revocation(s). July 1 deadline — hosts must reapply.")


def alert_scottsdale_new_licenses(licenses: list):
    if not licenses: return
    count = len(licenses)
    subject = f"[STRWatch] Scottsdale: {count} new STR license(s) detected"
    text = f"{count} new Scottsdale STR license(s). $250/yr fee, $1,000/violation enforcement."
    send_email(subject, f"<p>{text}</p>", text)


# ── Alert routing (calls router.send_city_alert for real user emails) ─────────

def route_legislation_alert(city: str, title: str, url: str, keywords: list):
    try:
        from alerts import router
        router.send_city_alert(
            city=city,
            subject=f"{city} — new STR legislation detected",
            headline=title,
            detail=f"STRWatch detected new STR-related legislation in {city}. Keywords matched: {', '.join(keywords[:3])}.",
            source_url=url,
            urgency="high",
        )
    except Exception as e:
        log.error("Alert routing failed: %s", e)


def route_page_change_alert(city: str, name: str, url: str, priority: str):
    try:
        from alerts import router
        router.send_city_alert(
            city=city,
            subject=f"{city} — regulation page updated",
            headline=f"{name} has been updated",
            detail=f"STRWatch detected a change on a monitored government page in {city}. Review the source for regulation updates.",
            source_url=url,
            urgency=priority,
        )
    except Exception as e:
        log.error("Alert routing failed: %s", e)
