"""
tests/test_reminders.py — Tests for the deadline reminder engine.

Covers:
- Reminder window matching (60, 30, 7 days)
- Dedup (same reminder not sent twice)
- User routing (city-level vs custom deadlines)
- Past deadlines ignored
- Urgency assignment by window
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import date, timedelta


class TestReminderWindows:
    """Test that reminders fire at exactly 60, 30, and 7 days."""

    def _make_deadline(self, days_from_now, city="Nashville, TN", user_id=None):
        deadline_date = (date.today() + timedelta(days=days_from_now)).isoformat()
        return {
            "id": f"dl-{days_from_now}",
            "city": city,
            "title": f"Test deadline ({days_from_now}d)",
            "description": "Test description",
            "deadline_date": deadline_date,
            "source_url": "https://example.com",
            "category": "permit",
            "user_id": user_id,
        }

    @patch('alerts.reminders.router')
    @patch('alerts.reminders.store')
    @patch('alerts.reminders._fetch_all_deadlines')
    def test_60_day_reminder_fires(self, mock_fetch, mock_store, mock_router):
        mock_fetch.return_value = [self._make_deadline(60)]
        mock_store.already_alerted.return_value = False
        mock_router.get_users_for_city.return_value = ["user_1"]
        mock_router.get_user_email.return_value = "test@example.com"
        mock_router.get_user_preferences.return_value = {"email_enabled": True, "sms_enabled": False}
        mock_router.get_user_tier.return_value = "pro"
        mock_router.send_alert_email.return_value = True
        mock_router.save_alert_to_supabase.return_value = True

        from alerts.reminders import check_and_send_reminders
        result = check_and_send_reminders()

        assert result["reminders_sent"] == 1
        mock_router.send_alert_email.assert_called_once()
        mock_store.record_alert.assert_called_once()

    @patch('alerts.reminders.router')
    @patch('alerts.reminders.store')
    @patch('alerts.reminders._fetch_all_deadlines')
    def test_30_day_reminder_fires(self, mock_fetch, mock_store, mock_router):
        mock_fetch.return_value = [self._make_deadline(30)]
        mock_store.already_alerted.return_value = False
        mock_router.get_users_for_city.return_value = ["user_1"]
        mock_router.get_user_email.return_value = "test@example.com"
        mock_router.get_user_preferences.return_value = {"email_enabled": True}
        mock_router.get_user_tier.return_value = "pro"
        mock_router.send_alert_email.return_value = True
        mock_router.save_alert_to_supabase.return_value = True

        from alerts.reminders import check_and_send_reminders
        result = check_and_send_reminders()
        assert result["reminders_sent"] == 1

    @patch('alerts.reminders.router')
    @patch('alerts.reminders.store')
    @patch('alerts.reminders._fetch_all_deadlines')
    def test_7_day_reminder_fires_with_sms(self, mock_fetch, mock_store, mock_router):
        mock_fetch.return_value = [self._make_deadline(7)]
        mock_store.already_alerted.return_value = False
        mock_router.get_users_for_city.return_value = ["user_1"]
        mock_router.get_user_email.return_value = "test@example.com"
        mock_router.get_user_preferences.return_value = {
            "email_enabled": True, "sms_enabled": True, "phone": "+15551234567"
        }
        mock_router.get_user_tier.return_value = "pro"
        mock_router.send_alert_email.return_value = True
        mock_router.send_sms_to_user.return_value = True
        mock_router.save_alert_to_supabase.return_value = True

        from alerts.reminders import check_and_send_reminders
        result = check_and_send_reminders()

        assert result["reminders_sent"] == 1
        mock_router.send_sms_to_user.assert_called_once()

    @patch('alerts.reminders.router')
    @patch('alerts.reminders.store')
    @patch('alerts.reminders._fetch_all_deadlines')
    def test_non_window_day_does_not_fire(self, mock_fetch, mock_store, mock_router):
        # 45 days is not a reminder window
        mock_fetch.return_value = [self._make_deadline(45)]
        mock_store.already_alerted.return_value = False

        from alerts.reminders import check_and_send_reminders
        result = check_and_send_reminders()

        assert result["reminders_sent"] == 0
        mock_router.send_alert_email.assert_not_called()

    @patch('alerts.reminders.router')
    @patch('alerts.reminders.store')
    @patch('alerts.reminders._fetch_all_deadlines')
    def test_past_deadline_ignored(self, mock_fetch, mock_store, mock_router):
        mock_fetch.return_value = [self._make_deadline(-5)]
        mock_store.already_alerted.return_value = False

        from alerts.reminders import check_and_send_reminders
        result = check_and_send_reminders()

        assert result["reminders_sent"] == 0


class TestReminderDedup:
    """Test that the same reminder doesn't fire twice."""

    def _make_deadline(self, days_from_now):
        return {
            "id": "dl-dedup-test",
            "city": "Austin, TX",
            "title": "Test deadline",
            "description": "",
            "deadline_date": (date.today() + timedelta(days=days_from_now)).isoformat(),
            "source_url": "",
            "category": "permit",
            "user_id": None,
        }

    @patch('alerts.reminders.router')
    @patch('alerts.reminders.store')
    @patch('alerts.reminders._fetch_all_deadlines')
    def test_already_alerted_skipped(self, mock_fetch, mock_store, mock_router):
        mock_fetch.return_value = [self._make_deadline(30)]
        mock_store.already_alerted.return_value = True  # Already sent

        from alerts.reminders import check_and_send_reminders
        result = check_and_send_reminders()

        assert result["reminders_sent"] == 0
        mock_router.send_alert_email.assert_not_called()

    @patch('alerts.reminders.router')
    @patch('alerts.reminders.store')
    @patch('alerts.reminders._fetch_all_deadlines')
    def test_dedup_key_includes_deadline_id_and_window(self, mock_fetch, mock_store, mock_router):
        mock_fetch.return_value = [self._make_deadline(30)]
        mock_store.already_alerted.return_value = False
        mock_router.get_users_for_city.return_value = ["user_1"]
        mock_router.get_user_email.return_value = "test@example.com"
        mock_router.get_user_preferences.return_value = {"email_enabled": True}
        mock_router.get_user_tier.return_value = "pro"
        mock_router.send_alert_email.return_value = True
        mock_router.save_alert_to_supabase.return_value = True

        from alerts.reminders import check_and_send_reminders
        check_and_send_reminders()

        # Check the dedup key format
        record_call = mock_store.record_alert.call_args
        alert_key = record_call[0][0]
        assert "reminder_dl-dedup-test_30d" == alert_key


class TestCustomDeadlineRouting:
    """Test that custom (user-specific) deadlines only go to that user."""

    @patch('alerts.reminders.router')
    @patch('alerts.reminders.store')
    @patch('alerts.reminders._fetch_all_deadlines')
    def test_custom_deadline_routes_to_owner_only(self, mock_fetch, mock_store, mock_router):
        mock_fetch.return_value = [{
            "id": "dl-custom",
            "city": "Nashville, TN",
            "title": "My permit renewal",
            "description": "",
            "deadline_date": (date.today() + timedelta(days=30)).isoformat(),
            "source_url": "",
            "category": "custom",
            "user_id": "user_owner",
        }]
        mock_store.already_alerted.return_value = False
        mock_router.get_user_email.return_value = "owner@example.com"
        mock_router.get_user_preferences.return_value = {"email_enabled": True}
        mock_router.get_user_tier.return_value = "pro"
        mock_router.send_alert_email.return_value = True
        mock_router.save_alert_to_supabase.return_value = True

        from alerts.reminders import check_and_send_reminders
        result = check_and_send_reminders()

        assert result["reminders_sent"] == 1
        # Should NOT have called get_users_for_city (routes directly to owner)
        mock_router.get_users_for_city.assert_not_called()
        # Should have sent to the owner
        mock_router.get_user_email.assert_called_once_with("user_owner")

    @patch('alerts.reminders.router')
    @patch('alerts.reminders.store')
    @patch('alerts.reminders._fetch_all_deadlines')
    def test_city_deadline_routes_to_all_watchers(self, mock_fetch, mock_store, mock_router):
        mock_fetch.return_value = [{
            "id": "dl-city",
            "city": "Denver, CO",
            "title": "Annual renewal",
            "description": "",
            "deadline_date": (date.today() + timedelta(days=7)).isoformat(),
            "source_url": "",
            "category": "permit",
            "user_id": None,  # City-level
        }]
        mock_store.already_alerted.return_value = False
        mock_router.get_users_for_city.return_value = ["user_a", "user_b", "user_c"]
        mock_router.get_user_email.side_effect = ["a@test.com", "b@test.com", "c@test.com"]
        mock_router.get_user_preferences.return_value = {"email_enabled": True, "sms_enabled": False}
        mock_router.get_user_tier.return_value = "pro"
        mock_router.send_alert_email.return_value = True
        mock_router.save_alert_to_supabase.return_value = True

        from alerts.reminders import check_and_send_reminders
        result = check_and_send_reminders()

        assert result["reminders_sent"] == 1
        assert mock_router.send_alert_email.call_count == 3
        mock_router.get_users_for_city.assert_called_once_with("Denver, CO")


class TestUrgencyAssignment:
    """Test that urgency is set correctly based on days remaining."""

    def test_7_day_is_high(self):
        from alerts.reminders import _urgency_for_days
        assert _urgency_for_days(7) == "high"

    def test_30_day_is_medium(self):
        from alerts.reminders import _urgency_for_days
        assert _urgency_for_days(30) == "medium"

    def test_60_day_is_low(self):
        from alerts.reminders import _urgency_for_days
        assert _urgency_for_days(60) == "low"

    def test_3_day_is_high(self):
        from alerts.reminders import _urgency_for_days
        assert _urgency_for_days(3) == "high"

    def test_15_day_is_medium(self):
        from alerts.reminders import _urgency_for_days
        assert _urgency_for_days(15) == "medium"

    def test_90_day_is_low(self):
        from alerts.reminders import _urgency_for_days
        assert _urgency_for_days(90) == "low"
