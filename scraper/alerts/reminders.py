"""
alerts/reminders.py — Deadline reminder engine.

Checks all deadlines (city-level and user-custom) and sends
reminder emails at 60, 30, and 7 days before each deadline.

Called by run.py after scrapers complete.
Deduped: each (deadline_id, reminder_window) pair only fires once.
"""

import os
import logging
import requests
from datetime import datetime, timezone, date, timedelta
from typing import List
from dotenv import load_dotenv
load_dotenv()

from db import store
from alerts import router

log = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://vnybfdzcwwsluwyznayq.supabase.co")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

REMINDER_WINDOWS = [60, 30, 7]  # days before deadline


def _fetch_all_deadlines() -> List[dict]:
    """Fetch all deadlines from Supabase."""
    if not SUPABASE_SERVICE_KEY:
        log.warning("SUPABASE_SERVICE_ROLE_KEY not set — skipping reminders")
        return []
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/deadlines",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            },
            params={"select": "*", "order": "deadline_date.asc"},
            timeout=15,
        )
        if not resp.ok:
            log.error("Failed to fetch deadlines: %s %s", resp.status_code, resp.text)
            return []
        return resp.json()
    except Exception as e:
        log.error("Deadline fetch error: %s", e)
        return []


def _get_users_for_deadline(deadline: dict) -> List[str]:
    """
    Get user IDs who should receive this deadline reminder.
    - City-level deadlines (user_id is null): all users watching that city
    - Custom deadlines (user_id set): only that specific user
    """
    if deadline.get("user_id"):
        return [deadline["user_id"]]
    return router.get_users_for_city(deadline["city"])


def _urgency_for_days(days: int) -> str:
    if days <= 7:
        return "high"
    if days <= 30:
        return "medium"
    return "low"


def check_and_send_reminders() -> dict:
    """
    Main entry point. Check all deadlines and send reminders
    for those hitting a reminder window today.

    Returns stats dict.
    """
    log.info("=== Deadline reminders starting ===")

    deadlines = _fetch_all_deadlines()
    if not deadlines:
        log.info("No deadlines found")
        return {"checked": 0, "reminders_sent": 0}

    today = date.today()
    reminders_sent = 0
    checked = 0

    for dl in deadlines:
        checked += 1
        deadline_date_str = dl.get("deadline_date", "")
        if not deadline_date_str:
            continue

        try:
            deadline_date = date.fromisoformat(deadline_date_str[:10])
        except ValueError:
            log.warning("Invalid deadline date: %s", deadline_date_str)
            continue

        days_remaining = (deadline_date - today).days

        # Skip past deadlines
        if days_remaining < 0:
            continue

        # Check if we're at a reminder window
        for window in REMINDER_WINDOWS:
            if days_remaining != window:
                continue

            # Dedup key: deadline ID + window
            alert_key = f"reminder_{dl['id']}_{window}d"
            if store.already_alerted(alert_key):
                continue

            # Build reminder content
            city = dl["city"]
            title = dl["title"]
            urgency = _urgency_for_days(window)
            category = dl.get("category", "permit")
            description = dl.get("description", "")
            source_url = dl.get("source_url", "https://app.strwatch.io/dashboard/deadlines")

            headline = f"{title} — {window} days remaining"
            detail = f"Your deadline in {city} is {window} days away ({deadline_date.strftime('%B %d, %Y')}). "
            if description:
                detail += description
            else:
                detail += "Review your compliance status and take action before the deadline."

            # Get affected users
            user_ids = _get_users_for_deadline(dl)
            if not user_ids:
                log.debug("No users for deadline %s in %s", dl["id"], city)
                continue

            # Send to each user
            for user_id in user_ids:
                email = router.get_user_email(user_id)
                prefs = router.get_user_preferences(user_id)
                tier = router.get_user_tier(user_id)

                email_enabled = prefs.get("email_enabled", True)
                sms_enabled = prefs.get("sms_enabled", True)
                phone = prefs.get("phone", "")
                is_pro = tier in ("pro", "agency")

                # Send email
                if email and email_enabled:
                    router.send_alert_email(
                        to_email=email,
                        subject=f"{city} — {title} ({window} days left)",
                        city=city,
                        headline=headline,
                        detail=detail,
                        source_url=source_url,
                        urgency=urgency,
                    )

                # Send SMS for 7-day reminders to Pro users
                if is_pro and sms_enabled and phone and window <= 7:
                    router.send_sms_to_user(
                        phone=phone,
                        message=f"[STRWatch] {city}: {title} — {window} days left. Action required.",
                    )

                # Save to dashboard
                router.save_alert_to_supabase(
                    user_id=user_id,
                    city=city,
                    subject=f"Deadline reminder: {title}",
                    headline=headline,
                    detail=detail,
                    source_url=source_url,
                    urgency=urgency,
                )

            # Record alert to prevent resend
            store.record_alert(alert_key, "deadline_reminder", city,
                               f"{title} — {window}d reminder")
            reminders_sent += 1
            log.info("Reminder sent: %s — %dd remaining (%d users)", title, window, len(user_ids))

    log.info("Deadline reminders done — checked: %d | reminders sent: %d",
             checked, reminders_sent)
    return {"checked": checked, "reminders_sent": reminders_sent}


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    result = check_and_send_reminders()
    print(f"\nResult: {result}")
