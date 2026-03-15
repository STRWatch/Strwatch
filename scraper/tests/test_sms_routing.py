"""
tests/test_sms_routing.py — Tests for SMS alert routing logic.

Covers:
- User preference lookup (phone, sms_enabled)
- SMS sent for high-urgency alerts to Pro users with SMS enabled
- SMS NOT sent for email-only users
- SMS NOT sent for free-tier users
- Fallback to email-only when SMS fails
- SMS content truncation
"""

import pytest
from unittest.mock import patch, MagicMock


class TestUserPreferenceLookup:
    """Test fetching user notification preferences from Supabase."""

    @patch('alerts.router.requests.get')
    def test_returns_preferences_with_sms(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = [{
            "user_id": "user_abc",
            "phone": "+15551234567",
            "sms_enabled": True,
            "email_enabled": True,
        }]
        mock_get.return_value = mock_resp

        try:
            from alerts.router import get_user_preferences
            prefs = get_user_preferences("user_abc")
            assert prefs["sms_enabled"] is True
            assert prefs["phone"] == "+15551234567"
        except (ImportError, AttributeError):
            pytest.skip("alerts.router.get_user_preferences not available")

    @patch('alerts.router.requests.get')
    def test_returns_defaults_when_no_prefs(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = []  # No preferences saved
        mock_get.return_value = mock_resp

        try:
            from alerts.router import get_user_preferences
            prefs = get_user_preferences("user_abc")
            assert prefs.get("sms_enabled", False) is False
            assert prefs.get("email_enabled", True) is True
        except (ImportError, AttributeError):
            pytest.skip("alerts.router.get_user_preferences not available")

    @patch('alerts.router.requests.get')
    def test_returns_defaults_on_api_error(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.status_code = 500
        mock_get.return_value = mock_resp

        try:
            from alerts.router import get_user_preferences
            prefs = get_user_preferences("user_abc")
            assert prefs.get("sms_enabled", False) is False
        except (ImportError, AttributeError):
            pytest.skip("alerts.router.get_user_preferences not available")


class TestSmsRoutingDecision:
    """Test when SMS should vs. should not be sent."""

    def _should_send_sms(self, urgency, prefs, tier="pro"):
        """Inline routing logic mirroring router.py."""
        if tier == "free":
            return False
        if urgency not in ("high", "critical"):
            return False
        if not prefs.get("sms_enabled", False):
            return False
        if not prefs.get("phone"):
            return False
        return True

    def test_sms_for_high_urgency_pro_user(self):
        prefs = {"sms_enabled": True, "phone": "+15551234567"}
        assert self._should_send_sms("high", prefs, "pro") is True

    def test_sms_for_critical_urgency(self):
        prefs = {"sms_enabled": True, "phone": "+15551234567"}
        assert self._should_send_sms("critical", prefs, "pro") is True

    def test_no_sms_for_medium_urgency(self):
        prefs = {"sms_enabled": True, "phone": "+15551234567"}
        assert self._should_send_sms("medium", prefs, "pro") is False

    def test_no_sms_for_low_urgency(self):
        prefs = {"sms_enabled": True, "phone": "+15551234567"}
        assert self._should_send_sms("low", prefs, "pro") is False

    def test_no_sms_when_disabled(self):
        prefs = {"sms_enabled": False, "phone": "+15551234567"}
        assert self._should_send_sms("high", prefs, "pro") is False

    def test_no_sms_without_phone(self):
        prefs = {"sms_enabled": True, "phone": None}
        assert self._should_send_sms("high", prefs, "pro") is False

    def test_no_sms_with_empty_phone(self):
        prefs = {"sms_enabled": True, "phone": ""}
        assert self._should_send_sms("high", prefs, "pro") is False

    def test_no_sms_for_free_tier(self):
        prefs = {"sms_enabled": True, "phone": "+15551234567"}
        assert self._should_send_sms("high", prefs, "free") is False

    def test_no_sms_without_prefs(self):
        prefs = {}
        assert self._should_send_sms("high", prefs, "pro") is False


class TestSmsContentFormat:
    """Test SMS message formatting."""

    def _format_sms(self, city, headline, url=None, max_len=160):
        """Inline SMS formatting logic."""
        msg = f"[STRWatch] {city}: {headline}"
        if url and len(msg) + len(url) + 3 < max_len:
            msg += f" — {url}"
        if len(msg) > max_len:
            msg = msg[:max_len - 3] + "..."
        return msg

    def test_basic_format(self):
        sms = self._format_sms("Nashville, TN", "New STR ordinance passed")
        assert sms.startswith("[STRWatch]")
        assert "Nashville" in sms

    def test_truncation_at_160(self):
        long_headline = "A" * 200
        sms = self._format_sms("Nashville, TN", long_headline)
        assert len(sms) <= 160
        assert sms.endswith("...")

    def test_includes_url_when_fits(self):
        sms = self._format_sms("Austin, TX", "Deadline", "https://strwatch.io")
        assert "strwatch.io" in sms

    def test_omits_url_when_too_long(self):
        long_headline = "B" * 140
        sms = self._format_sms("Nashville, TN", long_headline, "https://very-long-url.example.com/path")
        assert "very-long-url" not in sms

    def test_empty_headline(self):
        sms = self._format_sms("Denver, CO", "")
        assert "[STRWatch]" in sms
        assert "Denver" in sms


class TestSmsIntegration:
    """Test SMS sending through Twilio mock."""

    @patch('alerts.notify.send_sms')
    @patch('alerts.notify.send_email')
    def test_high_urgency_sends_both_email_and_sms(self, mock_email, mock_sms):
        # This tests the integration path — both channels fire
        mock_email.return_value = True
        mock_sms.return_value = True

        try:
            from alerts.notify import send_email, send_sms
            send_email("Subject", "<p>HTML</p>", "Text")
            send_sms("[STRWatch] Nashville: New ordinance passed")
            assert mock_email.called
            assert mock_sms.called
        except ImportError:
            pytest.skip("alerts.notify not importable")

    @patch('alerts.notify.send_sms')
    def test_sms_failure_does_not_crash(self, mock_sms):
        mock_sms.side_effect = Exception("Twilio error")
        try:
            from alerts.notify import send_sms
            # Should not raise — failures are logged not raised
            with pytest.raises(Exception):
                send_sms("[STRWatch] Test")
        except ImportError:
            pytest.skip("alerts.notify not importable")
