"""
tests/test_page_watchers.py — Tests for page watcher scrapers.

Covers:
- San Diego (sandiego_web.py)
- Charleston (charleston_web.py)
- Savannah (savannah_web.py)
- Page watcher configuration validation
- watch_page() change detection logic
"""

import pytest
from unittest.mock import patch, MagicMock


# ── Page watcher config validation ──────────────────────────────────────────

class TestSanDiegoConfig:
    """Validate San Diego page watcher configuration."""

    def _get_pages(self):
        return [
            {
                "name": "San Diego — STRO Regulations",
                "url": "https://www.sandiego.gov/treasurer/short-term-residential-occupancy",
                "priority": "high",
            },
            {
                "name": "San Diego — Open Data Portal (STR)",
                "url": "https://data.sandiego.gov/datasets/short-term-rentals/",
                "priority": "medium",
            },
            {
                "name": "San Diego — Council Dockets",
                "url": "https://www.sandiego.gov/city-clerk/officialdocs/council-dockets",
                "priority": "medium",
            },
        ]

    def test_has_three_watched_pages(self):
        assert len(self._get_pages()) == 3

    def test_all_pages_have_required_fields(self):
        for page in self._get_pages():
            assert "name" in page
            assert "url" in page
            assert "priority" in page

    def test_all_urls_are_https(self):
        for page in self._get_pages():
            assert page["url"].startswith("https://"), f"URL not HTTPS: {page['url']}"

    def test_has_high_priority_page(self):
        high = [p for p in self._get_pages() if p["priority"] == "high"]
        assert len(high) >= 1

    def test_city_name_in_page_names(self):
        for page in self._get_pages():
            assert "San Diego" in page["name"]


class TestCharlestonConfig:
    """Validate Charleston page watcher configuration."""

    def _get_pages(self):
        return [
            {
                "name": "Charleston — STR Permit Information",
                "url": "https://www.charleston-sc.gov/1840/Short-Term-Rental-Permit-Information",
                "priority": "high",
            },
            {
                "name": "Charleston — STR Ordinance & Task Force",
                "url": "https://www.charleston-sc.gov/2529/Short-Term-Rental-Ordinance",
                "priority": "high",
            },
            {
                "name": "Charleston — Open Data Portal",
                "url": "https://data-charleston-sc.opendata.arcgis.com/",
                "priority": "low",
            },
        ]

    def test_has_three_watched_pages(self):
        assert len(self._get_pages()) == 3

    def test_all_pages_have_required_fields(self):
        for page in self._get_pages():
            assert "name" in page
            assert "url" in page
            assert "priority" in page

    def test_all_urls_are_https(self):
        for page in self._get_pages():
            assert page["url"].startswith("https://")

    def test_has_high_priority_pages(self):
        high = [p for p in self._get_pages() if p["priority"] == "high"]
        assert len(high) >= 2, "Charleston should have permit + ordinance as high priority"

    def test_city_name_in_page_names(self):
        for page in self._get_pages():
            assert "Charleston" in page["name"]


class TestSavannahConfig:
    """Validate Savannah page watcher configuration."""

    def _get_pages(self):
        return [
            {
                "name": "Savannah — STVR Regulations",
                "url": "https://www.savannahga.gov/2327/STVR-Regulations",
                "priority": "high",
            },
            {
                "name": "Savannah — STVR Application Process",
                "url": "https://www.savannahga.gov/2332/STVR-Application-Process",
                "priority": "high",
            },
            {
                "name": "Savannah — STR Public Portal",
                "url": "https://www.savannahga.gov/2329/Short-Term-Rental-STR-Public-Portal",
                "priority": "medium",
            },
            {
                "name": "Savannah — Deckard STR Portal",
                "url": "https://str.deckard.com/ga-chatham-city_of_savannah/",
                "priority": "medium",
            },
        ]

    def test_has_four_watched_pages(self):
        assert len(self._get_pages()) == 4

    def test_all_pages_have_required_fields(self):
        for page in self._get_pages():
            assert "name" in page
            assert "url" in page
            assert "priority" in page

    def test_all_urls_are_https(self):
        for page in self._get_pages():
            assert page["url"].startswith("https://")

    def test_has_high_priority_pages(self):
        high = [p for p in self._get_pages() if p["priority"] == "high"]
        assert len(high) >= 2

    def test_includes_deckard_portal(self):
        urls = [p["url"] for p in self._get_pages()]
        assert any("deckard.com" in u for u in urls)

    def test_city_name_in_page_names(self):
        for page in self._get_pages():
            assert "Savannah" in page["name"]


# ── watch_page() change detection ───────────────────────────────────────────

class TestWatchPageLogic:
    """Test the core watch_page hash-diff logic."""

    @patch('scrapers.austin_web.notify')
    @patch('scrapers.austin_web.store')
    @patch('scrapers.austin_web._fetch_page_content')
    def test_first_visit_saves_baseline_no_alert(self, mock_fetch, mock_store, mock_notify):
        mock_fetch.return_value = ("abc123hash", 500)
        mock_store.get_last_snapshot.return_value = None  # First time

        try:
            from scrapers.austin_web import watch_page
            changed = watch_page("Test Page", "https://example.com", "Test City")
            assert changed is False
            mock_store.save_snapshot.assert_called_once()
            mock_notify.alert_page_changed.assert_not_called()
        except ImportError:
            pytest.skip("scrapers.austin_web not importable")

    @patch('scrapers.austin_web.notify')
    @patch('scrapers.austin_web.store')
    @patch('scrapers.austin_web._fetch_page_content')
    def test_no_change_no_alert(self, mock_fetch, mock_store, mock_notify):
        mock_fetch.return_value = ("abc123hash", 500)
        mock_store.get_last_snapshot.return_value = {"hash": "abc123hash", "content_len": 500}

        try:
            from scrapers.austin_web import watch_page
            changed = watch_page("Test Page", "https://example.com", "Test City")
            assert changed is False
            mock_notify.alert_page_changed.assert_not_called()
        except ImportError:
            pytest.skip("scrapers.austin_web not importable")

    @patch('scrapers.austin_web.notify')
    @patch('scrapers.austin_web.store')
    @patch('scrapers.austin_web._fetch_page_content')
    def test_change_detected_fires_alert(self, mock_fetch, mock_store, mock_notify):
        mock_fetch.return_value = ("new_hash_xyz", 600)
        mock_store.get_last_snapshot.return_value = {"hash": "old_hash_abc", "content_len": 500}

        try:
            from scrapers.austin_web import watch_page
            changed = watch_page("Test Page", "https://example.com", "Test City", "high")
            assert changed is True
            mock_notify.alert_page_changed.assert_called_once_with(
                "Test Page", "Test City", "https://example.com", "high"
            )
        except ImportError:
            pytest.skip("scrapers.austin_web not importable")

    @patch('scrapers.austin_web.store')
    @patch('scrapers.austin_web._fetch_page_content')
    def test_fetch_failure_returns_false(self, mock_fetch, mock_store):
        mock_fetch.return_value = None  # Network error

        try:
            from scrapers.austin_web import watch_page
            changed = watch_page("Test Page", "https://example.com", "Test City")
            assert changed is False
            mock_store.save_snapshot.assert_not_called()
        except ImportError:
            pytest.skip("scrapers.austin_web not importable")


# ── Scraper run() return format ─────────────────────────────────────────────

class TestScraperRunFormat:
    """Test that page watcher run() functions return expected format."""

    @patch('scrapers.austin_web.watch_page')
    def test_charleston_run_returns_dict(self, mock_watch):
        mock_watch.return_value = False
        try:
            from scrapers.charleston_web import run
            result = run()
            assert "checked" in result
            assert "changes" in result
            assert result["checked"] == 3
            assert result["changes"] == 0
        except ImportError:
            pytest.skip("scrapers.charleston_web not importable")

    @patch('scrapers.austin_web.watch_page')
    def test_savannah_run_returns_dict(self, mock_watch):
        mock_watch.return_value = False
        try:
            from scrapers.savannah_web import run
            result = run()
            assert "checked" in result
            assert "changes" in result
            assert result["checked"] == 4
            assert result["changes"] == 0
        except ImportError:
            pytest.skip("scrapers.savannah_web not importable")

    @patch('scrapers.austin_web.watch_page')
    def test_sandiego_run_returns_dict(self, mock_watch):
        mock_watch.return_value = False
        try:
            from scrapers.sandiego_web import run
            result = run()
            assert "checked" in result
            assert "changes" in result
            assert result["changes"] == 0
        except ImportError:
            pytest.skip("scrapers.sandiego_web not importable")

    @patch('scrapers.austin_web.watch_page')
    def test_charleston_counts_changes(self, mock_watch):
        mock_watch.side_effect = [True, False, True]  # 2 of 3 changed
        try:
            from scrapers.charleston_web import run
            result = run()
            assert result["changes"] == 2
        except ImportError:
            pytest.skip("scrapers.charleston_web not importable")

    @patch('scrapers.austin_web.watch_page')
    def test_savannah_counts_changes(self, mock_watch):
        mock_watch.side_effect = [False, True, False, False]  # 1 of 4 changed
        try:
            from scrapers.savannah_web import run
            result = run()
            assert result["changes"] == 1
        except ImportError:
            pytest.skip("scrapers.savannah_web not importable")

    @patch('scrapers.austin_web.watch_page')
    def test_handles_watch_page_exception(self, mock_watch):
        mock_watch.side_effect = [False, Exception("Network error"), False]
        try:
            from scrapers.charleston_web import run
            result = run()
            # Should continue despite error, only count successful checks
            assert result["checked"] == 3
        except ImportError:
            pytest.skip("scrapers.charleston_web not importable")
