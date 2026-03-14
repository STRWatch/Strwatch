"""
tests/test_checklist.py — Tests for the AI compliance checklist generator.

Covers:
- Output structure validation
- HTML formatting
- Plain text formatting
- Graceful failure when API key missing
- Graceful failure when anthropic not installed
"""

import pytest
import json
from unittest.mock import patch, MagicMock


class TestGenerateChecklist:
    """Test checklist generation logic (mocking the API call)."""

    def _mock_api_response(self, content_text):
        """Create a mock Anthropic API response."""
        mock_block = MagicMock()
        mock_block.text = content_text
        mock_message = MagicMock()
        mock_message.content = [mock_block]
        return mock_message

    @patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-test-key'})
    @patch('anthropic.Anthropic')
    def test_returns_valid_structure(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = self._mock_api_response(json.dumps({
            "summary": "Nashville requires permit renewal by April 15.",
            "urgency": "high",
            "deadline": "April 15, 2026",
            "steps": [
                {"step": 1, "action": "Check permit type", "detail": "Review your current permit classification."},
                {"step": 2, "action": "Submit renewal", "detail": "File renewal through Metro portal."},
            ]
        }))

        from alerts.checklist import generate_checklist
        result = generate_checklist(
            city="Nashville, TN",
            title="Permit renewal required",
            keywords=["STR", "permit cap"],
            source_url="https://example.com",
        )

        assert result is not None
        assert "steps" in result
        assert len(result["steps"]) == 2
        assert result["urgency"] == "high"
        assert result["deadline"] == "April 15, 2026"
        assert result["summary"] == "Nashville requires permit renewal by April 15."
        assert "raw_text" in result

    @patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-test-key'})
    @patch('anthropic.Anthropic')
    def test_steps_have_required_fields(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = self._mock_api_response(json.dumps({
            "summary": "Test",
            "urgency": "medium",
            "deadline": None,
            "steps": [
                {"step": 1, "action": "Do thing", "detail": "Details here"},
                {"step": 2, "action": "Do other thing", "detail": "More details"},
            ]
        }))

        from alerts.checklist import generate_checklist
        result = generate_checklist(
            city="Denver, CO", title="Test regulation",
            keywords=["STR"], source_url="",
        )

        for step in result["steps"]:
            assert "step" in step
            assert "action" in step
            assert "detail" in step

    @patch.dict('os.environ', {'ANTHROPIC_API_KEY': ''})
    def test_returns_none_when_no_api_key(self):
        from alerts.checklist import generate_checklist
        # Reload to pick up empty env var
        import importlib
        import alerts.checklist
        importlib.reload(alerts.checklist)

        result = alerts.checklist.generate_checklist(
            city="Nashville, TN", title="Test",
            keywords=["STR"], source_url="",
        )
        assert result is None

    @patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-test-key'})
    @patch('anthropic.Anthropic')
    def test_handles_malformed_json(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = self._mock_api_response(
            "This is not valid JSON at all"
        )

        from alerts.checklist import generate_checklist
        result = generate_checklist(
            city="Austin, TX", title="Test",
            keywords=["STR"], source_url="",
        )
        assert result is None

    @patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-test-key'})
    @patch('anthropic.Anthropic')
    def test_handles_json_without_steps(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = self._mock_api_response(json.dumps({
            "summary": "Test", "urgency": "low",
        }))

        from alerts.checklist import generate_checklist
        result = generate_checklist(
            city="Denver, CO", title="Test",
            keywords=["STR"], source_url="",
        )
        assert result is None

    @patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-test-key'})
    @patch('anthropic.Anthropic')
    def test_strips_markdown_fences(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        json_content = json.dumps({
            "summary": "Test", "urgency": "medium", "deadline": None,
            "steps": [{"step": 1, "action": "Do thing", "detail": "Details"}]
        })
        mock_client.messages.create.return_value = self._mock_api_response(
            f"```json\n{json_content}\n```"
        )

        from alerts.checklist import generate_checklist
        result = generate_checklist(
            city="Nashville, TN", title="Test",
            keywords=["STR"], source_url="",
        )
        assert result is not None
        assert len(result["steps"]) == 1


class TestFormatChecklistHtml:
    """Test HTML formatting of checklists."""

    def test_returns_empty_for_none(self):
        from alerts.checklist import format_checklist_html
        assert format_checklist_html(None) == ""

    def test_returns_empty_for_no_steps(self):
        from alerts.checklist import format_checklist_html
        assert format_checklist_html({"summary": "test"}) == ""
        assert format_checklist_html({"steps": []}) == ""

    def test_includes_steps_in_html(self):
        from alerts.checklist import format_checklist_html
        result = {
            "summary": "You need to renew.",
            "urgency": "high",
            "deadline": "April 15",
            "steps": [
                {"step": 1, "action": "Check permit", "detail": "Review your type."},
                {"step": 2, "action": "Submit form", "detail": "File online."},
            ]
        }
        html = format_checklist_html(result)
        assert "Check permit" in html
        assert "Submit form" in html
        assert "April 15" in html
        assert "AI COMPLIANCE CHECKLIST" in html
        assert "Urgent" in html  # high urgency label

    def test_medium_urgency_label(self):
        from alerts.checklist import format_checklist_html
        result = {
            "urgency": "medium",
            "steps": [{"step": 1, "action": "Test", "detail": "Test detail"}]
        }
        html = format_checklist_html(result)
        assert "Action needed" in html

    def test_low_urgency_label(self):
        from alerts.checklist import format_checklist_html
        result = {
            "urgency": "low",
            "steps": [{"step": 1, "action": "Test", "detail": "Test detail"}]
        }
        html = format_checklist_html(result)
        assert "FYI" in html

    def test_no_deadline_no_crash(self):
        from alerts.checklist import format_checklist_html
        result = {
            "urgency": "medium", "deadline": None,
            "steps": [{"step": 1, "action": "Test", "detail": "Test"}]
        }
        html = format_checklist_html(result)
        assert "DEADLINE" not in html
        assert "Test" in html


class TestFormatChecklistText:
    """Test plain text formatting."""

    def test_includes_steps(self):
        from alerts.checklist import _format_checklist_text
        result = {
            "summary": "Renewal required.",
            "deadline": "April 15",
            "steps": [
                {"step": 1, "action": "Check permit", "detail": "Review type."},
                {"step": 2, "action": "Submit form", "detail": "File online."},
            ]
        }
        text = _format_checklist_text(result, "Nashville, TN", "Test title")
        assert "Nashville, TN" in text
        assert "Check permit" in text
        assert "Submit form" in text
        assert "DEADLINE: April 15" in text

    def test_no_deadline(self):
        from alerts.checklist import _format_checklist_text
        result = {
            "summary": "Test",
            "steps": [{"step": 1, "action": "Do thing", "detail": "Details"}]
        }
        text = _format_checklist_text(result, "Denver, CO", "Test")
        assert "DEADLINE" not in text
        assert "Do thing" in text
