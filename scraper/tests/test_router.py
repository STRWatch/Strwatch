"""
tests/test_router.py — Tests for the alert routing engine.

Covers:
- User lookup by city
- Email lookup via Clerk
- Alert email sending with checklist HTML
- Alert saving to Supabase
- Handling of missing users / failed lookups
"""

import pytest
from unittest.mock import patch, MagicMock


class TestGetUsersForCity:
    @patch('alerts.router.requests.get')
    def test_returns_user_ids(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = [
            {"user_id": "user_abc"},
            {"user_id": "user_def"},
        ]
        mock_get.return_value = mock_resp

        from alerts.router import get_users_for_city
        users = get_users_for_city("Nashville, TN")
        assert users == ["user_abc", "user_def"]

    @patch('alerts.router.requests.get')
    def test_returns_empty_on_error(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.status_code = 500
        mock_resp.text = "Internal error"
        mock_get.return_value = mock_resp

        from alerts.router import get_users_for_city
        users = get_users_for_city("Nashville, TN")
        assert users == []

    @patch('alerts.router.SUPABASE_SERVICE_KEY', '')
    def test_returns_empty_without_key(self):
        from alerts.router import get_users_for_city
        users = get_users_for_city("Nashville, TN")
        assert users == []


class TestGetUserEmail:
    @patch('alerts.router.requests.get')
    def test_returns_primary_email(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {
            "primary_email_address_id": "email_1",
            "email_addresses": [
                {"id": "email_1", "email_address": "host@example.com"},
                {"id": "email_2", "email_address": "alt@example.com"},
            ]
        }
        mock_get.return_value = mock_resp

        from alerts.router import get_user_email
        email = get_user_email("user_abc")
        assert email == "host@example.com"

    @patch('alerts.router.requests.get')
    def test_falls_back_to_first_email(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {
            "primary_email_address_id": "email_nonexistent",
            "email_addresses": [
                {"id": "email_1", "email_address": "fallback@example.com"},
            ]
        }
        mock_get.return_value = mock_resp

        from alerts.router import get_user_email
        email = get_user_email("user_abc")
        assert email == "fallback@example.com"

    @patch('alerts.router.requests.get')
    def test_returns_none_on_api_error(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        from alerts.router import get_user_email
        email = get_user_email("user_nonexistent")
        assert email is None


class TestSendCityAlert:
    @patch('alerts.router.save_alert_to_supabase')
    @patch('alerts.router.send_alert_email')
    @patch('alerts.router.get_user_email')
    @patch('alerts.router.get_users_for_city')
    def test_sends_to_all_users_in_city(
        self, mock_get_users, mock_get_email, mock_send, mock_save
    ):
        mock_get_users.return_value = ["user_1", "user_2"]
        mock_get_email.side_effect = ["host1@example.com", "host2@example.com"]
        mock_send.return_value = True
        mock_save.return_value = True

        from alerts.router import send_city_alert
        result = send_city_alert(
            city="Nashville, TN",
            subject="Test alert",
            headline="Test headline",
            detail="Test detail",
            source_url="https://example.com",
            urgency="high",
            checklist_html="<div>Checklist</div>",
        )

        assert result["users"] == 2
        assert result["sent"] == 2
        assert result["failed"] == 0
        assert mock_send.call_count == 2
        assert mock_save.call_count == 2

    @patch('alerts.router.save_alert_to_supabase')
    @patch('alerts.router.send_alert_email')
    @patch('alerts.router.get_user_email')
    @patch('alerts.router.get_users_for_city')
    def test_handles_email_lookup_failure(
        self, mock_get_users, mock_get_email, mock_send, mock_save
    ):
        mock_get_users.return_value = ["user_1", "user_2"]
        mock_get_email.side_effect = [None, "host2@example.com"]
        mock_send.return_value = True
        mock_save.return_value = True

        from alerts.router import send_city_alert
        result = send_city_alert(
            city="Nashville, TN",
            subject="Test",
            headline="Test",
            detail="Test",
            source_url="",
            urgency="medium",
        )

        assert result["sent"] == 1
        assert result["failed"] == 1

    @patch('alerts.router.get_users_for_city')
    def test_no_users_watching_city(self, mock_get_users):
        mock_get_users.return_value = []

        from alerts.router import send_city_alert
        result = send_city_alert(
            city="Charleston, SC",
            subject="Test",
            headline="Test",
            detail="Test",
            source_url="",
        )

        assert result["users"] == 0
        assert result["sent"] == 0

    @patch('alerts.router.save_alert_to_supabase')
    @patch('alerts.router.send_alert_email')
    @patch('alerts.router.get_user_email')
    @patch('alerts.router.get_users_for_city')
    def test_checklist_html_passed_to_email(
        self, mock_get_users, mock_get_email, mock_send, mock_save
    ):
        mock_get_users.return_value = ["user_1"]
        mock_get_email.return_value = "host@example.com"
        mock_send.return_value = True
        mock_save.return_value = True

        from alerts.router import send_city_alert
        send_city_alert(
            city="Austin, TX",
            subject="Test",
            headline="Test",
            detail="Test",
            source_url="",
            urgency="high",
            checklist_html="<div>AI Checklist Here</div>",
        )

        # Verify checklist_html was passed to send_alert_email
        send_call = mock_send.call_args
        assert send_call[1].get('checklist_html') == "<div>AI Checklist Here</div>" or \
               (len(send_call[0]) >= 8 and send_call[0][7] == "<div>AI Checklist Here</div>")
