"""
tests/test_email_safety.py — Escaping / sanitizing of untrusted content in
alert emails and checklist HTML.

Everything interpolated into email HTML comes from a scraped page, the LLM,
or the database and must be html.escape()d. source_url is only ever placed in
an href when it starts with https://.
"""

import pytest
from unittest.mock import patch, MagicMock

XSS = '<script>alert("x")</script>'
XSS_ESC = '&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;'


def _captured_resend_html(mock_post):
    return mock_post.call_args[1]["json"]["html"]


class TestRouterEmailEscaping:
    @patch('alerts.router.RESEND_API_KEY', 're_test')
    @patch('alerts.router.requests.post')
    def test_headline_detail_city_are_escaped(self, mock_post):
        mock_post.return_value = MagicMock(ok=True)
        from alerts.router import send_alert_email
        send_alert_email(
            "h@example.com", "subj", f"Austin{XSS}",
            f"Head{XSS}", f"Det{XSS}", "https://ok.example.com", "high",
        )
        html = _captured_resend_html(mock_post)
        assert XSS not in html
        assert html.count(XSS_ESC) >= 3  # city (x2 in template), headline, detail

    @patch('alerts.router.RESEND_API_KEY', 're_test')
    @patch('alerts.router.requests.post')
    def test_https_source_url_becomes_href(self, mock_post):
        mock_post.return_value = MagicMock(ok=True)
        from alerts.router import send_alert_email
        send_alert_email("h@example.com", "s", "Austin", "h", "d",
                         "https://austintexas.gov/str?a=1&b=2", "low")
        html = _captured_resend_html(mock_post)
        assert 'href="https://austintexas.gov/str?a=1&amp;b=2"' in html

    @pytest.mark.parametrize("bad", [
        "javascript:alert(1)",
        "http://insecure.example.com/x",
        "//evil.example.com/x",
        '" onmouseover="alert(1)',
    ])
    @patch('alerts.router.RESEND_API_KEY', 're_test')
    @patch('alerts.router.requests.post')
    def test_non_https_source_url_is_text_not_href(self, mock_post, bad):
        mock_post.return_value = MagicMock(ok=True)
        from alerts.router import send_alert_email
        send_alert_email("h@example.com", "s", "Austin", "h", "d", bad, "low")
        html = _captured_resend_html(mock_post)
        assert f'href="{bad}"' not in html
        assert "href=" not in html.split("View source")[0].split("Manage notifications")[0] \
            or 'href="https://app.strwatch.io' in html
        import html as _h
        assert _h.escape(bad, quote=True) in html

    def test_safe_href_helper(self):
        from alerts.router import safe_href
        assert safe_href("https://x.gov/a?b=1&c=2") == "https://x.gov/a?b=1&amp;c=2"
        assert safe_href("HTTPS://x.gov") is not None
        assert safe_href("http://x.gov") is None
        assert safe_href("//x.gov") is None
        assert safe_href("javascript:alert(1)") is None
        assert safe_href("") is None
        assert safe_href(None) is None

    @patch('alerts.router.RESEND_API_KEY', 're_test')
    @patch('alerts.router.requests.post')
    def test_checklist_html_is_passed_through_unescaped(self, mock_post):
        # checklist_html is already sanitized by alerts.checklist; router must
        # not double-escape it.
        mock_post.return_value = MagicMock(ok=True)
        from alerts.router import send_alert_email
        send_alert_email("h@example.com", "s", "Austin", "h", "d",
                         "https://x.gov", "low", checklist_html="<ol><li>Do it</li></ol>")
        assert "<ol><li>Do it</li></ol>" in _captured_resend_html(mock_post)


class TestNotifyEscaping:
    @patch('alerts.notify.route_page_change_alert')
    @patch('alerts.notify.store')
    @patch('alerts.notify.send_sms')
    @patch('alerts.notify.send_email')
    @patch('alerts.notify._generate_checklist_safe', return_value={})
    def test_page_changed_escapes_name_city_and_url(self, _cl, mock_email, _sms, mock_store, _route):
        mock_store.already_alerted.return_value = False
        from alerts.notify import alert_page_changed
        alert_page_changed(name=f"Page{XSS}", city=f"City{XSS}",
                           url='javascript:alert(1)', priority="high")
        html = mock_email.call_args[0][1]
        assert XSS not in html
        assert XSS_ESC in html
        assert 'href="javascript:alert(1)"' not in html
        assert "javascript:alert(1)" in html  # shown as text

    @patch('alerts.notify.route_page_change_alert')
    @patch('alerts.notify.store')
    @patch('alerts.notify.send_sms')
    @patch('alerts.notify.send_email')
    @patch('alerts.notify._generate_checklist_safe', return_value={})
    def test_page_changed_https_url_is_link(self, _cl, mock_email, _sms, mock_store, _route):
        mock_store.already_alerted.return_value = False
        from alerts.notify import alert_page_changed
        alert_page_changed(name="P", city="C", url="https://nashville.gov/str", priority="low")
        assert 'href="https://nashville.gov/str"' in mock_email.call_args[0][1]

    @patch('alerts.notify.route_legislation_alert')
    @patch('alerts.notify.store')
    @patch('alerts.notify.send_sms')
    @patch('alerts.notify.send_email')
    @patch('alerts.notify._generate_checklist_safe', return_value={})
    def test_legislation_escapes_title_bill_keywords(self, _cl, mock_email, _sms, mock_store, _route):
        mock_store.already_alerted.return_value = False
        from alerts.notify import alert_new_legislation
        alert_new_legislation(city="Nashville, TN", bill_id=f"BL{XSS}",
                              title=f"T{XSS}", url="http://insecure.gov/x",
                              keywords=[f"kw{XSS}"])
        html = mock_email.call_args[0][1]
        assert XSS not in html
        assert html.count(XSS_ESC) == 3
        assert 'href="http://insecure.gov/x"' not in html

    @patch('alerts.notify.store')
    @patch('alerts.notify.send_email')
    def test_denver_rows_escaped(self, mock_email, mock_store):
        mock_store.already_alerted.return_value = False
        from alerts.notify import alert_denver_new_licenses
        alert_denver_new_licenses([{"address": f"1 Main{XSS}", "license_type": "P",
                                    "status": "Active", "issued_date": "2026-01-01"}])
        html = mock_email.call_args[0][1]
        assert XSS not in html and XSS_ESC in html

    @patch('alerts.router.send_city_alert')
    @patch('alerts.notify.store')
    @patch('alerts.notify.send_email')
    def test_sandiego_detail_escaped(self, mock_email, mock_store, _route):
        mock_store.already_alerted.return_value = False
        from alerts.notify import alert_sandiego_new_licenses
        alert_sandiego_new_licenses([{"address": f"9 Beach{XSS}", "license_type": "1"}])
        html = mock_email.call_args[0][1]
        assert XSS not in html and XSS_ESC in html


class TestChecklistSanitizing:
    def test_llm_fields_are_escaped(self):
        from alerts.checklist import format_checklist_html
        html = format_checklist_html({
            "urgency": "high",
            "summary": f"Sum{XSS}",
            "deadline": f"Dead{XSS}",
            "steps": [{"step": 1, "action": f"Act{XSS}", "detail": f"Det{XSS}"}],
        })
        assert XSS not in html
        # nh3 re-serializes text nodes, so quotes may be unescaped; the tag
        # brackets are what matter.
        assert html.count("&lt;script&gt;") == 4
        assert "<script" not in html

    def test_output_uses_only_allowlisted_tags(self):
        import re
        from alerts.checklist import format_checklist_html, CHECKLIST_TAGS
        html = format_checklist_html({
            "urgency": "medium", "summary": "S", "deadline": "D",
            "steps": [{"step": 1, "action": "A", "detail": "B"}],
        })
        tags = set(re.findall(r"</?([a-zA-Z0-9]+)", html))
        assert tags <= CHECKLIST_TAGS
        assert "style=" not in html

    def test_sanitizer_strips_disallowed_tags_and_attrs(self):
        from alerts.checklist import sanitize_checklist_html
        out = sanitize_checklist_html(
            '<div style="x">d</div><script>bad()</script><p onclick="x">p</p>'
            '<img src="x" onerror="alert(1)"><h3>ok</h3><table><tr><td>t</td></tr></table>'
        )
        assert "<div" not in out and "<script" not in out and "<img" not in out
        assert "bad()" not in out
        assert "onclick" not in out
        assert "<p>p</p>" in out and "<h3>ok</h3>" in out and "t" in out

    @pytest.mark.parametrize("href,kept", [
        ("https://nashville.gov/str", True),
        ("http://nashville.gov/str", True),
        ("javascript:alert(1)", False),
        ("//evil.example.com/x", False),
        ("/relative/path", False),
        ("data:text/html,x", False),
        ("ftp://files.example.com", False),
    ])
    def test_sanitizer_href_schemes(self, href, kept):
        from alerts.checklist import sanitize_checklist_html
        out = sanitize_checklist_html(f'<a href="{href}" target="_blank" rel="x">L</a>')
        assert "target=" not in out and "rel=" not in out
        if kept:
            assert f'href="{href}"' in out
        else:
            assert "href=" not in out
            assert "L" in out  # text preserved

    def test_sanitizer_is_idempotent_on_formatter_output(self):
        from alerts.checklist import format_checklist_html, sanitize_checklist_html
        html = format_checklist_html({
            "urgency": "low", "summary": "S & <T>",
            "steps": [{"step": 1, "action": "A", "detail": "B"}],
        })
        assert sanitize_checklist_html(html) == html
