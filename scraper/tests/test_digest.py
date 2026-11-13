"""
tests/test_digest.py — Free-tier queuing in router.send_city_alert and the
weekly digest in alerts/digest.py.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta


# ── router: free vs non-free branch ──────────────────────────────────────────

class TestSendCityAlertTierBranch:
    def _run(self, tier, mock_send, mock_save, urgency="high"):
        from alerts.router import send_city_alert
        return send_city_alert(
            city="Austin, TX", subject="S", headline="H", detail="D",
            source_url="https://austintexas.gov", urgency=urgency,
            checklist_html="<ol><li>x</li></ol>",
        )

    @patch('alerts.router.send_sms_to_user', return_value=True)
    @patch('alerts.router.get_user_tier', return_value="free")
    @patch('alerts.router.get_user_preferences', return_value={"phone": "+15550001111", "sms_enabled": True})
    @patch('alerts.router.get_user_email', return_value="free@example.com")
    @patch('alerts.router.get_users_for_city', return_value=["user_free"])
    @patch('alerts.router.save_alert_to_supabase', return_value=True)
    @patch('alerts.router.send_alert_email', return_value=True)
    def test_free_user_is_queued_not_emailed(self, mock_send, mock_save, *_):
        result = self._run("free", mock_send, mock_save)
        mock_send.assert_not_called()
        mock_save.assert_called_once()
        assert mock_save.call_args[1]["sent"] is False
        assert mock_save.call_args[1]["checklist_json"] == "<ol><li>x</li></ol>"
        assert result["sent"] == 0
        assert result["queued"] == 1
        assert result["sms_sent"] == 0

    @pytest.mark.parametrize("tier", ["pro", "agency"])
    def test_paid_user_gets_realtime_email(self, tier):
        with patch('alerts.router.get_user_preferences', return_value={}), \
             patch('alerts.router.get_user_email', return_value="paid@example.com"), \
             patch('alerts.router.get_users_for_city', return_value=["user_paid"]), \
             patch('alerts.router.save_alert_to_supabase', return_value=True) as mock_save, \
             patch('alerts.router.send_alert_email', return_value=True) as mock_send, \
             patch('alerts.router.get_user_tier', return_value=tier):
            result = self._run(tier, mock_send, mock_save)
        mock_send.assert_called_once()
        mock_save.assert_called_once()
        assert mock_save.call_args[1].get("sent", True) is True
        assert result["sent"] == 1
        assert result["queued"] == 0

    @patch('alerts.router.get_user_preferences', return_value={})
    @patch('alerts.router.get_user_email', side_effect=["free@example.com", "pro@example.com"])
    @patch('alerts.router.get_users_for_city', return_value=["u_free", "u_pro"])
    @patch('alerts.router.save_alert_to_supabase', return_value=True)
    @patch('alerts.router.send_alert_email', return_value=True)
    def test_mixed_users(self, mock_send, mock_save, *_):
        with patch('alerts.router.get_user_tier', side_effect=["free", "pro"]):
            result = self._run(None, mock_send, mock_save)
        assert result == {"city": "Austin, TX", "users": 2, "sent": 1, "sms_sent": 0,
                          "failed": 0, "queued": 1}
        assert [c[1]["user_id"] for c in mock_save.call_args_list] == ["u_free", "u_pro"]
        assert mock_save.call_args_list[0][1]["sent"] is False


class TestGetUserTierTrial:
    def _tier_resp(self, tier, trial_ends_at):
        resp = MagicMock(ok=True)
        resp.json.return_value = [{"tier": tier, "trial_ends_at": trial_ends_at}]
        return resp

    @patch('alerts.router.requests.get')
    def test_active_trial_is_pro(self, mock_get):
        future = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat().replace("+00:00", "Z")
        mock_get.return_value = self._tier_resp("pro", future)
        from alerts.router import get_user_tier
        assert get_user_tier("u") == "pro"

    @patch('alerts.router.requests.get')
    def test_expired_trial_is_free(self, mock_get):
        past = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat().replace("+00:00", "Z")
        mock_get.return_value = self._tier_resp("pro", past)
        from alerts.router import get_user_tier
        assert get_user_tier("u") == "free"

    @patch('alerts.router.requests.get')
    def test_no_row_is_free(self, mock_get):
        resp = MagicMock(ok=True)
        resp.json.return_value = []
        mock_get.return_value = resp
        from alerts.router import get_user_tier
        assert get_user_tier("u") == "free"


class TestSaveAlertSentAt:
    @patch('alerts.router.requests.post')
    def test_sent_false_writes_null_sent_at(self, mock_post):
        mock_post.return_value = MagicMock(ok=True)
        from alerts.router import save_alert_to_supabase
        save_alert_to_supabase("u", "C", "s", "h", "d", "https://x", "low", sent=False)
        assert mock_post.call_args[1]["json"]["sent_at"] is None

    @patch('alerts.router.requests.post')
    def test_default_writes_timestamp(self, mock_post):
        mock_post.return_value = MagicMock(ok=True)
        from alerts.router import save_alert_to_supabase
        save_alert_to_supabase("u", "C", "s", "h", "d", "https://x", "low")
        assert mock_post.call_args[1]["json"]["sent_at"]


# ── digest ───────────────────────────────────────────────────────────────────

ROWS = [
    {"id": 1, "user_id": "u1", "city": "Austin, TX", "headline": "A1", "detail": "d1",
     "source_url": "https://austin.gov/1", "urgency": "high"},
    {"id": 2, "user_id": "u2", "city": "Denver, CO", "headline": "B1", "detail": "d",
     "source_url": "http://insecure/x", "urgency": "low"},
    {"id": 3, "user_id": "u1", "city": "Nashville, TN", "headline": "A2 <b>x</b>", "detail": "<i>d2</i>",
     "source_url": "javascript:alert(1)", "urgency": "medium"},
    {"id": 4, "user_id": "u1", "city": "Austin, TX", "headline": "A3", "detail": "d3",
     "source_url": "", "urgency": "high"},
]


class TestDigestGrouping:
    def test_groups_by_user_then_city_preserving_order(self):
        from alerts.digest import group_alerts
        g = group_alerts(ROWS)
        assert list(g.keys()) == ["u1", "u2"]
        assert list(g["u1"].keys()) == ["Austin, TX", "Nashville, TN"]
        assert [a["id"] for a in g["u1"]["Austin, TX"]] == [1, 4]
        assert [a["id"] for a in g["u1"]["Nashville, TN"]] == [3]
        assert [a["id"] for a in g["u2"]["Denver, CO"]] == [2]

    def test_skips_rows_without_user(self):
        from alerts.digest import group_alerts
        assert group_alerts([{"id": 9, "city": "X"}]) == {}


class TestDigestEmail:
    def test_email_lists_cities_and_escapes(self):
        from alerts.digest import group_alerts, build_digest_email
        email = build_digest_email(group_alerts(ROWS)["u1"])
        assert "3 updates in 2 markets" in email["subject"]
        html = email["html"]
        assert html.index("Austin, TX") < html.index("Nashville, TN")
        assert "A2 &lt;b&gt;x&lt;/b&gt;" in html
        assert "&lt;i&gt;d2&lt;/i&gt;" in html
        assert "<b>x</b>" not in html
        assert 'href="https://austin.gov/1"' in html
        assert 'href="javascript:alert(1)"' not in html
        assert "javascript:alert(1)" in html  # as text
        assert "Urgent" in html and "Heads up" in html
        assert "A1" in email["text"] and "Nashville, TN" in email["text"]

    def test_http_url_is_text_not_link(self):
        from alerts.digest import group_alerts, build_digest_email
        html = build_digest_email(group_alerts(ROWS)["u2"])["html"]
        assert 'href="http://insecure/x"' not in html
        assert "http://insecure/x" in html

    def test_singular_subject(self):
        from alerts.digest import group_alerts, build_digest_email
        assert "1 update in 1 market" in build_digest_email(group_alerts(ROWS)["u2"])["subject"]


class TestDigestRun:
    @patch('alerts.digest.mark_sent', return_value=True)
    @patch('alerts.digest.send_digest_email', return_value=True)
    @patch('alerts.digest.router.get_user_email', side_effect=["one@example.com", "two@example.com"])
    @patch('alerts.digest.fetch_pending_alerts', return_value=ROWS)
    def test_sends_one_email_per_user_and_marks_rows(self, _fetch, _email, mock_send, mock_mark):
        from alerts.digest import run
        result = run()
        assert mock_send.call_count == 2
        assert mock_send.call_args_list[0][0][0] == "one@example.com"
        assert mock_mark.call_args_list[0][0][0] == [1, 4, 3]
        assert mock_mark.call_args_list[1][0][0] == [2]
        assert result == {"pending": 4, "users": 2, "sent": 2, "failed": 0, "marked": 4, "dry_run": False}

    @patch('alerts.digest.mark_sent', return_value=True)
    @patch('alerts.digest.send_digest_email', return_value=True)
    @patch('alerts.digest.router.get_user_email', return_value="x@example.com")
    @patch('alerts.digest.fetch_pending_alerts', return_value=ROWS)
    def test_dry_run_sends_and_marks_nothing(self, _fetch, _email, mock_send, mock_mark):
        from alerts.digest import run
        result = run(dry_run=True)
        mock_send.assert_not_called()
        mock_mark.assert_not_called()
        assert result["dry_run"] is True and result["users"] == 2 and result["sent"] == 0

    @patch('alerts.digest.mark_sent', return_value=True)
    @patch('alerts.digest.send_digest_email', return_value=False)
    @patch('alerts.digest.router.get_user_email', return_value="x@example.com")
    @patch('alerts.digest.fetch_pending_alerts', return_value=ROWS[:1])
    def test_failed_send_leaves_rows_pending(self, _fetch, _email, _send, mock_mark):
        from alerts.digest import run
        result = run()
        mock_mark.assert_not_called()
        assert result["failed"] == 1 and result["marked"] == 0

    @patch('alerts.digest.mark_sent', return_value=True)
    @patch('alerts.digest.send_digest_email', return_value=True)
    @patch('alerts.digest.router.get_user_email', return_value=None)
    @patch('alerts.digest.fetch_pending_alerts', return_value=ROWS[:1])
    def test_missing_email_leaves_rows_pending(self, _fetch, _email, mock_send, mock_mark):
        from alerts.digest import run
        result = run()
        mock_send.assert_not_called()
        mock_mark.assert_not_called()
        assert result["failed"] == 1

    @patch('alerts.digest.requests.patch')
    def test_mark_sent_uses_in_filter(self, mock_patch):
        mock_patch.return_value = MagicMock(ok=True)
        from alerts.digest import mark_sent
        assert mark_sent([1, 2]) is True
        assert mock_patch.call_args[1]["params"] == {"id": "in.(1,2)"}
        assert mock_patch.call_args[1]["json"]["sent_at"]

    @patch('alerts.digest.requests.get')
    def test_fetch_filters_null_sent_at(self, mock_get):
        resp = MagicMock(ok=True)
        resp.json.return_value = ROWS
        mock_get.return_value = resp
        from alerts.digest import fetch_pending_alerts
        assert fetch_pending_alerts() == ROWS
        assert mock_get.call_args[1]["params"]["sent_at"] == "is.null"
