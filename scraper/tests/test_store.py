"""
tests/test_store.py — Tests for db/store.py persistence layer.

Uses an in-memory SQLite database to test:
- Denver license upsert (new, update, revocation detection)
- Legislation dedup (same bill_id not inserted twice)
- Alert dedup (same alert_key not sent twice)
- Page snapshot tracking
"""

import pytest
import sqlite3
import json
from unittest.mock import patch
from datetime import datetime, timezone


@pytest.fixture
def test_db(tmp_path):
    """Set up a temporary SQLite DB and patch config.DB_PATH."""
    db_path = tmp_path / "test_strwatch.db"
    with patch("config.DB_PATH", db_path):
        from db import store
        store.init_db()
        # Create austin_licenses table (normally done by first run)
        conn = store.get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS austin_licenses (
                license_id TEXT PRIMARY KEY, license_type TEXT, status TEXT,
                address TEXT, street_name TEXT, zip_code TEXT,
                neighborhood TEXT, council_district TEXT, owner_name TEXT,
                issued_date TEXT, expiry_date TEXT,
                first_seen TEXT, last_updated TEXT, raw_json TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scottsdale_licenses (
                license_id TEXT PRIMARY KEY, address TEXT, owner_name TEXT,
                mgmt_company TEXT, emerg_contact TEXT, emerg_phone TEXT,
                property_score TEXT, status TEXT DEFAULT 'active',
                first_seen TEXT, last_updated TEXT, raw_json TEXT
            )
        """)
        conn.commit()
        yield store


class TestDenverUpsert:
    def test_new_license_is_new(self, test_db):
        result = test_db.upsert_denver_license({
            "license_id": "DEN-001",
            "address": "100 Main St",
            "status": "Active",
            "license_type": "Primary",
            "raw": {"test": True},
        })
        assert result["is_new"] is True
        assert result["was_revoked"] is False

    def test_same_license_not_new_on_second_upsert(self, test_db):
        record = {
            "license_id": "DEN-002", "address": "200 Oak", "status": "Active",
            "license_type": "Primary", "raw": {},
        }
        test_db.upsert_denver_license(record)
        result = test_db.upsert_denver_license(record)
        assert result["is_new"] is False
        assert result["was_revoked"] is False

    def test_revocation_detected(self, test_db):
        test_db.upsert_denver_license({
            "license_id": "DEN-003", "status": "Active", "raw": {},
        })
        result = test_db.upsert_denver_license({
            "license_id": "DEN-003", "status": "Revoked", "raw": {},
        })
        assert result["is_new"] is False
        assert result["was_revoked"] is True

    def test_expiration_detected(self, test_db):
        test_db.upsert_denver_license({
            "license_id": "DEN-004", "status": "Active", "raw": {},
        })
        result = test_db.upsert_denver_license({
            "license_id": "DEN-004", "status": "Expired", "raw": {},
        })
        assert result["was_revoked"] is True

    def test_already_revoked_not_re_flagged(self, test_db):
        test_db.upsert_denver_license({
            "license_id": "DEN-005", "status": "Active", "raw": {},
        })
        test_db.upsert_denver_license({
            "license_id": "DEN-005", "status": "Revoked", "raw": {},
        })
        # Third upsert: still revoked — should NOT re-flag
        result = test_db.upsert_denver_license({
            "license_id": "DEN-005", "status": "Revoked", "raw": {},
        })
        assert result["was_revoked"] is False

    def test_stats_reflect_data(self, test_db):
        test_db.upsert_denver_license({"license_id": "DEN-S1", "status": "Active", "raw": {}})
        test_db.upsert_denver_license({"license_id": "DEN-S2", "status": "Active", "raw": {}})
        test_db.upsert_denver_license({"license_id": "DEN-S3", "status": "Revoked", "raw": {}})
        stats = test_db.get_denver_stats()
        assert stats["total"] == 3
        assert stats["active"] >= 2  # "Active" matches the LIKE '%active%' query


class TestLegislationDedup:
    def test_new_bill_returns_true(self, test_db):
        is_new = test_db.save_legislation(
            city="Nashville", source="Legistar", bill_id="BL2026-001",
            title="Test bill", description="", status="Introduced",
            introduced_date="2026-03-01", url="https://example.com",
            keyword_matches=["STR"], raw={"test": True},
        )
        assert is_new is True

    def test_same_bill_returns_false(self, test_db):
        test_db.save_legislation(
            city="Nashville", source="Legistar", bill_id="BL2026-002",
            title="Test bill 2", description="", status="Introduced",
            introduced_date="2026-03-01", url="https://example.com",
            keyword_matches=["STR"], raw={},
        )
        is_new = test_db.save_legislation(
            city="Nashville", source="Legistar", bill_id="BL2026-002",
            title="Updated title", description="", status="Passed",
            introduced_date="2026-03-01", url="https://example.com",
            keyword_matches=["STR", "vacation rental"], raw={},
        )
        assert is_new is False

    def test_same_bill_id_different_city_is_new(self, test_db):
        test_db.save_legislation(
            city="Nashville", source="Legistar", bill_id="BL-100",
            title="Nashville bill", description="", status="", introduced_date="",
            url="", keyword_matches=[], raw={},
        )
        is_new = test_db.save_legislation(
            city="Austin", source="CouncilAgenda", bill_id="BL-100",
            title="Austin bill", description="", status="", introduced_date="",
            url="", keyword_matches=[], raw={},
        )
        assert is_new is True


class TestAlertDedup:
    def test_first_alert_not_already_sent(self, test_db):
        assert test_db.already_alerted("test_key_1") is False

    def test_recorded_alert_is_deduped(self, test_db):
        test_db.record_alert("test_key_2", "page_changed", "Nashville", "test")
        assert test_db.already_alerted("test_key_2") is True

    def test_different_keys_not_confused(self, test_db):
        test_db.record_alert("key_a", "legislation", "Austin", "bill A")
        assert test_db.already_alerted("key_a") is True
        assert test_db.already_alerted("key_b") is False


class TestPageSnapshots:
    def test_first_snapshot_returns_none(self, test_db):
        last = test_db.get_last_snapshot("https://example.com/test")
        assert last is None

    def test_snapshot_saved_and_retrieved(self, test_db):
        url = "https://example.com/str-page"
        test_db.save_snapshot(url, "Test Page", "Nashville", "abc123", 500, changed=False)
        last = test_db.get_last_snapshot(url)
        assert last is not None
        assert last["hash"] == "abc123"
        assert last["content_len"] == 500

    def test_latest_snapshot_returned(self, test_db):
        url = "https://example.com/changing-page"
        test_db.save_snapshot(url, "Page", "Denver", "hash_old", 100, changed=False)
        test_db.save_snapshot(url, "Page", "Denver", "hash_new", 200, changed=True)
        last = test_db.get_last_snapshot(url)
        assert last["hash"] == "hash_new"
        assert last["content_len"] == 200
