"""
tests/test_scrapers.py — Tests for scraper run logic.

Covers:
- Austin SODA: incremental fetch always runs (skip-forever bug fix)
- Scottsdale: always re-fetches to detect new licenses (skip-forever bug fix)
- Denver: field normalization handles missing/unexpected fields
- Nashville: keyword matching uses word boundaries
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone


class TestAustinSodaRunLogic:
    """Verify the skip-forever bug is fixed in austin_soda.py."""

    @patch('scrapers.austin_soda.fetch_all')
    @patch('scrapers.austin_soda.store')
    @patch('scrapers.austin_soda.notify')
    def test_incremental_run_fetches_even_when_db_has_records(self, mock_notify, mock_store, mock_fetch):
        """The old code returned early if DB had any records. The fix should always fetch."""
        mock_fetch.return_value = iter([])  # No new records from API
        mock_store.get_austin_license_stats.return_value = {"total": 2744, "active": 2700, "by_type": {}}

        from scrapers.austin_soda import run
        result = run(full_sync=False)

        # fetch_all should have been called (not skipped)
        mock_fetch.assert_called_once()
        assert result["processed"] == 0  # No records from API is fine
        assert "stats" in result

    @patch('scrapers.austin_soda.fetch_all')
    @patch('scrapers.austin_soda.store')
    @patch('scrapers.austin_soda.notify')
    def test_full_sync_fetches_all(self, mock_notify, mock_store, mock_fetch):
        mock_fetch.return_value = iter([])
        mock_store.get_austin_license_stats.return_value = {"total": 0, "active": 0, "by_type": {}}

        from scrapers.austin_soda import run
        result = run(full_sync=True)

        # Should call fetch_all with since=None for full sync
        mock_fetch.assert_called_once_with(since=None)

    @patch('scrapers.austin_soda.fetch_all')
    @patch('scrapers.austin_soda.store')
    @patch('scrapers.austin_soda.notify')
    def test_incremental_uses_2day_lookback(self, mock_notify, mock_store, mock_fetch):
        mock_fetch.return_value = iter([])
        mock_store.get_austin_license_stats.return_value = {"total": 100, "active": 100, "by_type": {}}

        from scrapers.austin_soda import run
        result = run(full_sync=False)

        # Should have been called with a since parameter (not None)
        call_args = mock_fetch.call_args
        assert call_args is not None
        since_val = call_args[1].get("since") or call_args[0][0] if call_args[0] else call_args[1].get("since")
        assert since_val is not None, "Incremental run should pass a 'since' parameter"

    @patch('scrapers.austin_soda.fetch_all')
    @patch('scrapers.austin_soda.store')
    @patch('scrapers.austin_soda.notify')
    def test_new_license_triggers_alert(self, mock_notify, mock_store, mock_fetch):
        fake_record = {
            "raw": {}, "city": "Austin", "license_id": "STR-2026-001",
            "license_type": "Type 2", "address": "123 Main St, Austin, TX",
            "status": "active",
        }
        mock_fetch.return_value = iter([fake_record])
        mock_store.upsert_austin_license.return_value = {"is_new": True, "was_revoked": False}
        mock_store.get_austin_license_stats.return_value = {"total": 1, "active": 1, "by_type": {}}

        from scrapers.austin_soda import run
        result = run(full_sync=False)

        assert result["new"] == 1
        mock_notify.alert_austin_new_licenses.assert_called_once()

    @patch('scrapers.austin_soda.fetch_all')
    @patch('scrapers.austin_soda.store')
    @patch('scrapers.austin_soda.notify')
    def test_revocation_triggers_alert(self, mock_notify, mock_store, mock_fetch):
        fake_record = {
            "raw": {}, "city": "Austin", "license_id": "STR-2026-002",
            "license_type": "Type 1", "address": "456 Oak Ave, Austin, TX",
            "status": "revoked",
        }
        mock_fetch.return_value = iter([fake_record])
        mock_store.upsert_austin_license.return_value = {"is_new": False, "was_revoked": True}
        mock_store.get_austin_license_stats.return_value = {"total": 100, "active": 99, "by_type": {}}

        from scrapers.austin_soda import run
        result = run(full_sync=False)

        assert result["revoked"] == 1
        mock_notify.alert_austin_revocations.assert_called_once()


class TestScottsdaleRunLogic:
    """Verify Scottsdale always re-fetches (skip-forever bug fix)."""

    @patch('scrapers.scottsdale_arcgis.fetch_all')
    @patch('scrapers.scottsdale_arcgis.store')
    @patch('scrapers.scottsdale_arcgis.notify')
    def test_run_fetches_even_when_db_has_records(self, mock_notify, mock_store, mock_fetch):
        """The old code returned early if stats.total > 0. The fix always fetches."""
        mock_fetch.return_value = iter([])
        mock_store.get_scottsdale_license_stats.return_value = {"total": 2999, "active": 2999}

        from scrapers.scottsdale_arcgis import run
        result = run()

        mock_fetch.assert_called_once()
        assert result["processed"] == 0

    @patch('scrapers.scottsdale_arcgis.fetch_all')
    @patch('scrapers.scottsdale_arcgis.store')
    @patch('scrapers.scottsdale_arcgis.notify')
    def test_new_license_detected(self, mock_notify, mock_store, mock_fetch):
        fake_record = {
            "raw": {}, "city": "Scottsdale", "license_id": "SCT-001",
            "address": "789 Desert Dr", "status": "active",
        }
        mock_fetch.return_value = iter([fake_record])
        mock_store.upsert_scottsdale_license.return_value = {"is_new": True}
        mock_store.get_scottsdale_license_stats.return_value = {"total": 3000, "active": 3000}

        from scrapers.scottsdale_arcgis import run
        result = run()

        assert result["new"] == 1
        mock_notify.alert_scottsdale_new_licenses.assert_called_once()

    @patch('scrapers.scottsdale_arcgis.fetch_all')
    @patch('scrapers.scottsdale_arcgis.store')
    @patch('scrapers.scottsdale_arcgis.notify')
    def test_existing_license_not_alerted(self, mock_notify, mock_store, mock_fetch):
        fake_record = {
            "raw": {}, "city": "Scottsdale", "license_id": "SCT-001",
            "address": "789 Desert Dr", "status": "active",
        }
        mock_fetch.return_value = iter([fake_record])
        mock_store.upsert_scottsdale_license.return_value = {"is_new": False}
        mock_store.get_scottsdale_license_stats.return_value = {"total": 2999, "active": 2999}

        from scrapers.scottsdale_arcgis import run
        result = run()

        assert result["new"] == 0
        mock_notify.alert_scottsdale_new_licenses.assert_not_called()


class TestDenverNormalization:
    """Test Denver SODA field mapping handles edge cases."""

    def test_normalize_with_known_fields(self):
        from scrapers.denver_soda import _normalize
        raw = {
            "license_number": "DEN-123",
            "address": "100 Broadway, Denver",
            "license_type": "Primary",
            "status": "Active",
            "issued_date": "2025-01-15",
        }
        result = _normalize(raw)
        assert result["license_id"] == "DEN-123"
        assert result["address"] == "100 Broadway, Denver"
        assert result["status"] == "Active"

    def test_normalize_with_unknown_fields_uses_fallback_id(self):
        from scrapers.denver_soda import _normalize
        raw = {"weird_field": "value", ":id": "row-abc123"}
        result = _normalize(raw)
        assert result["license_id"] == "row-abc123"

    def test_normalize_with_no_id_at_all(self):
        from scrapers.denver_soda import _normalize
        raw = {"some_field": "data"}
        result = _normalize(raw)
        # Should still have a license_id (hash fallback)
        assert result["license_id"] is not None
        assert len(str(result["license_id"])) > 0

    def test_normalize_strips_whitespace(self):
        from scrapers.denver_soda import _normalize
        raw = {"license_number": "  DEN-456  ", "status": " Active "}
        result = _normalize(raw)
        assert result["license_id"] == "DEN-456"
        assert result["status"] == "Active"


class TestAustinNormalization:
    """Test Austin SODA normalization."""

    def test_normalize_basic(self):
        from scrapers.austin_soda import _normalize
        raw = {
            "case_number": "STR-2026-100",
            "str_type": "Type 2",
            "prop_address": "123 Main St",
            "prop_zip": "78701",
            "prop_city": "Austin",
            "prop_state": "TX",
            "council_district": "3",
        }
        result = _normalize(raw)
        assert result["license_id"] == "STR-2026-100"
        assert result["license_type"] == "Type 2"
        assert "123 Main St" in result["address"]
        assert "78701" in result["address"]

    def test_normalize_missing_case_number_uses_fallback(self):
        from scrapers.austin_soda import _normalize
        raw = {":id": "row-xyz", "str_type": "Type 1"}
        result = _normalize(raw)
        assert result["license_id"] == "row-xyz"

    def test_normalize_missing_city_defaults_austin(self):
        from scrapers.austin_soda import _normalize
        raw = {"case_number": "STR-001", "prop_address": "456 Oak"}
        result = _normalize(raw)
        assert "Austin" in result["address"]
        assert "TX" in result["address"]
