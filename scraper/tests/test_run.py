"""
tests/test_run.py — run.py orchestration: scrape_runs logging, result
classification, and the process exit code.
"""

import sys
import types
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone


def _fake_module(run_impl):
    mod = types.ModuleType("scrapers.fake_source")
    mod.run = run_impl
    return mod


class TestClassifyResult:
    @pytest.mark.parametrize("result,expected", [
        ({"checked": 5, "changes": 0}, ("ok", 0)),
        ({"checked": 5, "changes": 2}, ("changed", 2)),
        ({"processed": 10, "new": 1, "revoked": 2, "errors": 0}, ("changed", 3)),
        ({"page_changes": 1, "new_agenda_items": 0}, ("changed", 1)),
        ({"checked": 3, "new_bills": 0, "errors": 2}, ("ok", 0)),
        ({"cities_scanned": 3, "total_new_bills": 4, "total_errors": 0}, ("changed", 4)),
        ({"changes": [{"a": 1}, {"b": 2}]}, ("changed", 2)),  # list-valued
        ({}, ("ok", 0)),
        (None, ("ok", 0)),
    ])
    def test_classify(self, result, expected):
        import run
        assert run.classify_result(result) == expected


class TestRunStep:
    @patch('run.record_scrape_run')
    def test_ok_run_records_ok(self, mock_rec):
        import run
        fake = _fake_module(lambda: {"checked": 4, "changes": 0})
        results = {}
        with patch('run.importlib.import_module', return_value=fake):
            run.run_step(results, "charleston", "Charleston", "scrapers.charleston_web", "Charleston scraper")
        assert results == {"charleston": {"checked": 4, "changes": 0}}
        mock_rec.assert_called_once()
        args = mock_rec.call_args[0]
        assert args[0] == "charleston"
        assert args[1] == "Charleston, SC"
        assert isinstance(args[2], datetime) and args[2].tzinfo is not None
        assert args[3] == "ok" and args[4] == 0

    @patch('run.record_scrape_run')
    def test_changed_run_records_changed(self, mock_rec):
        import run
        fake = _fake_module(lambda full_sync=False: {"processed": 9, "new": 2, "revoked": 1, "errors": 0})
        results = {}
        with patch('run.importlib.import_module', return_value=fake):
            run.run_step(results, "denver", "Denver", "scrapers.denver_soda", "Denver scraper",
                         call=lambda m: m.run(full_sync=True))
        args = mock_rec.call_args[0]
        assert args[3] == "changed" and args[4] == 3

    @patch('run.record_scrape_run')
    def test_exception_records_error_with_traceback(self, mock_rec):
        import run

        def boom():
            raise ValueError("kaboom " + "x" * 1000)

        fake = _fake_module(boom)
        results = {}
        with patch('run.importlib.import_module', return_value=fake):
            run.run_step(results, "state_pages", "State", "scrapers.state_pages_web", "State pages scraper")
        assert results["state_pages"]["error"].startswith("kaboom")
        args = mock_rec.call_args[0]
        assert args[0] == "state_pages" and args[1] is None
        assert args[3] == "error" and args[4] == 0
        err = args[5]
        assert "Traceback" in err and "ValueError" in err
        assert len(err) <= 500

    @patch('run.record_scrape_run', side_effect=RuntimeError("db down"))
    def test_scrape_runs_failure_never_aborts(self, _rec):
        # record_scrape_run itself never raises, but even if it did the
        # scraper result must survive. Here we assert run_step does not
        # propagate and the result is kept.
        import run
        fake = _fake_module(lambda: {"checked": 1, "changes": 1})
        results = {}
        with patch('run.importlib.import_module', return_value=fake):
            try:
                run.run_step(results, "boston", "Boston", "scrapers.boston_web", "Boston scraper")
            except RuntimeError:
                pytest.fail("run_step propagated a scrape_runs write failure")
        assert results["boston"] == {"checked": 1, "changes": 1}


class TestRecordScrapeRun:
    @patch.dict('os.environ', {"SUPABASE_URL": "https://p.supabase.co", "SUPABASE_SERVICE_ROLE_KEY": "k"})
    @patch('requests.post')
    def test_posts_row(self, mock_post):
        import run
        mock_post.return_value = MagicMock(ok=True)
        started = datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc)
        assert run.record_scrape_run("austin", "Austin, TX", started, "changed", 2) is True
        kw = mock_post.call_args[1]
        assert mock_post.call_args[0][0].endswith("/rest/v1/scrape_runs")
        assert kw["json"]["source"] == "austin"
        assert kw["json"]["city"] == "Austin, TX"
        assert kw["json"]["started_at"] == "2026-01-01T08:00:00+00:00"
        assert kw["json"]["finished_at"]
        assert kw["json"]["status"] == "changed"
        assert kw["json"]["pages_changed"] == 2
        assert kw["json"]["error"] is None
        assert kw["headers"]["Authorization"] == "Bearer k"

    @patch.dict('os.environ', {"SUPABASE_URL": "https://p.supabase.co", "SUPABASE_SERVICE_ROLE_KEY": "k"})
    @patch('requests.post')
    def test_error_truncated_to_500(self, mock_post):
        import run
        mock_post.return_value = MagicMock(ok=True)
        run.record_scrape_run("x", None, datetime.now(timezone.utc), "error", 0, "e" * 2000)
        assert len(mock_post.call_args[1]["json"]["error"]) == 500

    @patch.dict('os.environ', {"SUPABASE_URL": "https://p.supabase.co", "SUPABASE_SERVICE_ROLE_KEY": "k"})
    @patch('requests.post', side_effect=ConnectionError("no network"))
    def test_network_error_is_swallowed(self, _post):
        import run
        assert run.record_scrape_run("x", None, datetime.now(timezone.utc), "ok") is False

    @patch.dict('os.environ', {"SUPABASE_URL": "https://p.supabase.co", "SUPABASE_SERVICE_ROLE_KEY": "k"})
    @patch('requests.post')
    def test_http_error_is_swallowed(self, mock_post):
        import run
        mock_post.return_value = MagicMock(ok=False, status_code=500, text="boom")
        assert run.record_scrape_run("x", None, datetime.now(timezone.utc), "ok") is False

    @patch.dict('os.environ', {"SUPABASE_URL": "", "SUPABASE_SERVICE_ROLE_KEY": ""})
    @patch('requests.post')
    def test_skips_without_env(self, mock_post):
        import run
        assert run.record_scrape_run("x", None, datetime.now(timezone.utc), "ok") is False
        mock_post.assert_not_called()
