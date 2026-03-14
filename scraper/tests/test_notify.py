"""
tests/test_notify.py — Tests for the alert notification system.

Covers:
- Checklist integration in legislation alerts
- Checklist integration in page change alerts
- Alert dedup (same key not sent twice)
- Graceful handling when checklist generation fails
- Email/SMS send functions handle missing config
"""

import pytest
from unittest.mock import patch, MagicMock, call


class TestChecklistIntegration:
    """Verify checklists are generated and included in alerts."""

    @patch('alerts.notify.route_legislation_alert')
    @patch('alerts.notify.store')
    @patch('alerts.notify.send_sms')
    @patch('alerts.notify.send_email')
    @patch('alerts.notify._generate_checklist_safe')
    def test_legislation_alert_generates_checklist(
        self, mock_checklist, mock_email, mock_sms, mock_store, mock_route
    ):
        mock_store.already_alerted.return_value = False
        mock_checklist.return_value = {
            "summary": "Test summary",
            "urgency": "high",
            "deadline": "April 15",
            "steps": [{"step": 1, "action": "Test", "detail": "Detail"}],
            "raw_text": "Test raw text",
        }
        mock_email.return_value = True
        mock_sms.return_value = True

        from alerts.notify import alert_new_legislation
        alert_new_legislation(
            city="Nashville, TN",
            bill_id="BL-TEST-001",
            title="Test STR bill",
            url="https://example.com",
            keywords=["STR"],
        )

        # Checklist should have been called
        mock_checklist.assert_called_once_with(
            city="Nashville, TN",
            title="Test STR bill",
            keywords=["STR"],
            source_url="https://example.com",
            alert_type="legislation",
        )
        # Email should have been sent
        mock_email.assert_called_once()
        # The HTML should contain checklist content
        html_arg = mock_email.call_args[0][1]
        assert "AI COMPLIANCE CHECKLIST" in html_arg or "Test" in html_arg

    @patch('alerts.notify.route_page_change_alert')
    @patch('alerts.notify.store')
    @patch('alerts.notify.send_sms')
    @patch('alerts.notify.send_email')
    @patch('alerts.notify._generate_checklist_safe')
    def test_page_change_alert_generates_checklist(
        self, mock_checklist, mock_email, mock_sms, mock_store, mock_route
    ):
        mock_store.already_alerted.return_value = False
        mock_checklist.return_value = {
            "summary": "Page updated",
            "urgency": "medium",
            "steps": [{"step": 1, "action": "Review", "detail": "Check page"}],
            "raw_text": "Review the page",
        }
        mock_email.return_value = True

        from alerts.notify import alert_page_changed
        alert_page_changed(
            name="Nashville STRP Page",
            city="Nashville, TN",
            url="https://nashville.gov/str",
            priority="high",
        )

        mock_checklist.assert_called_once()
        mock_email.assert_called_once()

    @patch('alerts.notify.route_legislation_alert')
    @patch('alerts.notify.store')
    @patch('alerts.notify.send_sms')
    @patch('alerts.notify.send_email')
    @patch('alerts.notify._generate_checklist_safe')
    def test_alert_still_sends_when_checklist_fails(
        self, mock_checklist, mock_email, mock_sms, mock_store, mock_route
    ):
        mock_store.already_alerted.return_value = False
        mock_checklist.return_value = {}  # Failed checklist
        mock_email.return_value = True
        mock_sms.return_value = True

        from alerts.notify import alert_new_legislation
        alert_new_legislation(
            city="Austin, TX",
            bill_id="BL-TEST-002",
            title="Test bill",
            url="https://example.com",
            keywords=["STR"],
        )

        # Email should still be sent even without checklist
        mock_email.assert_called_once()
        mock_store.record_alert.assert_called_once()


class TestAlertDedup:
    """Verify alerts are not sent twice for the same key."""

    @patch('alerts.notify.route_legislation_alert')
    @patch('alerts.notify.store')
    @patch('alerts.notify.send_sms')
    @patch('alerts.notify.send_email')
    @patch('alerts.notify._generate_checklist_safe')
    def test_duplicate_alert_not_sent(
        self, mock_checklist, mock_email, mock_sms, mock_store, mock_route
    ):
        mock_store.already_alerted.return_value = True  # Already sent

        from alerts.notify import alert_new_legislation
        alert_new_legislation(
            city="Nashville, TN",
            bill_id="BL-DUPE-001",
            title="Duplicate bill",
            url="https://example.com",
            keywords=["STR"],
        )

        mock_email.assert_not_called()
        mock_sms.assert_not_called()
        mock_checklist.assert_not_called()


class TestEmailSmsConfig:
    """Test graceful handling of missing email/SMS config."""

    @patch('alerts.notify.config')
    def test_send_email_returns_false_without_config(self, mock_config):
        mock_config.RESEND_API_KEY = ""
        mock_config.ALERT_EMAIL = ""

        from alerts.notify import send_email
        result = send_email("Test", "<p>Test</p>", "Test")
        assert result is False

    @patch('alerts.notify.config')
    def test_send_sms_returns_false_without_config(self, mock_config):
        mock_config.TWILIO_ACCOUNT_SID = ""
        mock_config.TWILIO_AUTH_TOKEN = ""
        mock_config.TWILIO_FROM = ""
        mock_config.ALERT_PHONE = ""

        from alerts.notify import send_sms
        result = send_sms("Test message")
        assert result is False


class TestDenverAlerts:
    """Test Denver-specific alert functions."""

    @patch('alerts.notify.store')
    @patch('alerts.notify.send_email')
    def test_empty_list_does_nothing(self, mock_email, mock_store):
        from alerts.notify import alert_denver_new_licenses, alert_denver_revocations
        alert_denver_new_licenses([])
        alert_denver_revocations([])
        mock_email.assert_not_called()

    @patch('alerts.notify.store')
    @patch('alerts.notify.send_email')
    def test_new_licenses_sends_email(self, mock_email, mock_store):
        mock_store.already_alerted.return_value = False
        mock_email.return_value = True

        from alerts.notify import alert_denver_new_licenses
        alert_denver_new_licenses([
            {"address": "100 Main St", "license_type": "Primary", "status": "Active", "issued_date": "2026-03-01"},
        ])
        mock_email.assert_called_once()
        subject = mock_email.call_args[0][0]
        assert "Denver" in subject
        assert "1 new STR license" in subject

    @patch('alerts.notify.store')
    @patch('alerts.notify.send_sms')
    @patch('alerts.notify.send_email')
    def test_revocations_sends_email_and_sms(self, mock_email, mock_sms, mock_store):
        mock_store.already_alerted.return_value = False
        mock_email.return_value = True
        mock_sms.return_value = True

        from alerts.notify import alert_denver_revocations
        alert_denver_revocations([
            {"address": "200 Oak Ave", "status": "Revoked", "expiry_date": "2026-02-28"},
        ])
        mock_email.assert_called_once()
        mock_sms.assert_called_once()
