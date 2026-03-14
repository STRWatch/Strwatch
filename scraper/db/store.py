"""
db/store.py — Persistent storage for STRWatch scraper.

Uses SQLite locally. Set USE_SUPABASE=True in config to switch backends.
The interface is identical either way — just swap the backend.
"""

from typing import Optional
import sqlite3
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import config

log = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── SQLite backend ────────────────────────────────────────────────────────────

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create all tables if they don't exist."""
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS page_snapshots (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                url         TEXT NOT NULL,
                name        TEXT NOT NULL,
                city        TEXT NOT NULL,
                hash        TEXT NOT NULL,
                content_len INTEGER,
                checked_at  TEXT NOT NULL,
                changed     INTEGER DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_snapshots_url ON page_snapshots(url);

            CREATE TABLE IF NOT EXISTS denver_licenses (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                license_id      TEXT UNIQUE,
                address         TEXT,
                license_type    TEXT,
                status          TEXT,
                issued_date     TEXT,
                expiry_date     TEXT,
                owner_name      TEXT,
                neighborhood    TEXT,
                raw_json        TEXT,
                first_seen_at   TEXT NOT NULL,
                last_seen_at    TEXT NOT NULL,
                is_new          INTEGER DEFAULT 1,
                was_revoked     INTEGER DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_denver_license_id ON denver_licenses(license_id);
            CREATE INDEX IF NOT EXISTS idx_denver_status ON denver_licenses(status);

            CREATE TABLE IF NOT EXISTS legislation (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                city            TEXT NOT NULL,
                source          TEXT NOT NULL,
                bill_id         TEXT,
                title           TEXT,
                description     TEXT,
                status          TEXT,
                introduced_date TEXT,
                url             TEXT,
                keyword_matches TEXT,
                raw_json        TEXT,
                first_seen_at   TEXT NOT NULL
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_legislation_bill ON legislation(city, bill_id);

            CREATE TABLE IF NOT EXISTS alerts_sent (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_key   TEXT UNIQUE NOT NULL,
                alert_type  TEXT,
                city        TEXT,
                summary     TEXT,
                sent_at     TEXT NOT NULL
            );
        """)
    log.info("DB initialized at %s", config.DB_PATH)


# ── Page snapshot helpers ─────────────────────────────────────────────────────

def get_last_snapshot(url: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM page_snapshots WHERE url=? ORDER BY checked_at DESC LIMIT 1",
            (url,)
        ).fetchone()
        return dict(row) if row else None


def save_snapshot(url: str, name: str, city: str, hash_val: str, content_len: int, changed: bool):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO page_snapshots (url, name, city, hash, content_len, checked_at, changed)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (url, name, city, hash_val, content_len, _now(), int(changed))
        )


# ── Denver license helpers ────────────────────────────────────────────────────

def get_known_license_ids() -> set:
    with get_conn() as conn:
        rows = conn.execute("SELECT license_id FROM denver_licenses").fetchall()
        return {r["license_id"] for r in rows}


def get_active_license_ids() -> set:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT license_id FROM denver_licenses WHERE status NOT LIKE '%revok%' AND status NOT LIKE '%expir%'"
        ).fetchall()
        return {r["license_id"] for r in rows}


def upsert_denver_license(record: dict) -> dict:
    """
    Insert new license or update existing. Returns a dict with:
    - is_new: True if this license_id was never seen before
    - was_revoked: True if status changed to revoked/expired
    """
    lid = record.get("license_id")
    now = _now()

    with get_conn() as conn:
        existing = conn.execute(
            "SELECT status, first_seen_at FROM denver_licenses WHERE license_id=?", (lid,)
        ).fetchone()

        new_status = record.get("status", "")
        is_new = existing is None
        was_revoked = False

        if existing:
            old_status = existing["status"] or ""
            is_revocation = (
                ("revok" in new_status.lower() or "expir" in new_status.lower() or "inactiv" in new_status.lower())
                and "revok" not in old_status.lower()
                and "expir" not in old_status.lower()
            )
            was_revoked = is_revocation

            conn.execute("""
                UPDATE denver_licenses
                SET status=?, last_seen_at=?, raw_json=?, was_revoked=?
                WHERE license_id=?
            """, (new_status, now, json.dumps(record.get("raw")), int(is_revocation or existing["was_revoked"] if "was_revoked" in existing.keys() else 0), lid))
        else:
            conn.execute("""
                INSERT INTO denver_licenses
                    (license_id, address, license_type, status, issued_date, expiry_date,
                     owner_name, neighborhood, raw_json, first_seen_at, last_seen_at, is_new, was_revoked)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0)
            """, (
                lid,
                record.get("address"),
                record.get("license_type"),
                new_status,
                record.get("issued_date"),
                record.get("expiry_date"),
                record.get("owner_name"),
                record.get("neighborhood"),
                json.dumps(record.get("raw")),
                now, now
            ))

    return {"is_new": is_new, "was_revoked": was_revoked}


def get_denver_stats() -> dict:
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) as n FROM denver_licenses").fetchone()["n"]
        active = conn.execute(
            "SELECT COUNT(*) as n FROM denver_licenses WHERE status LIKE '%active%' OR status LIKE '%issued%'"
        ).fetchone()["n"]
        new_today = conn.execute(
            "SELECT COUNT(*) as n FROM denver_licenses WHERE is_new=1 AND first_seen_at >= date('now')"
        ).fetchone()["n"]
        revoked_today = conn.execute(
            "SELECT COUNT(*) as n FROM denver_licenses WHERE was_revoked=1 AND last_seen_at >= date('now')"
        ).fetchone()["n"]
        return {"total": total, "active": active, "new_today": new_today, "revoked_today": revoked_today}


# ── Legislation helpers ───────────────────────────────────────────────────────

def save_legislation(city: str, source: str, bill_id: str, title: str,
                     description: str, status: str, introduced_date: str,
                     url: str, keyword_matches: list, raw: dict) -> bool:
    """Returns True if this is a newly seen bill."""
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM legislation WHERE city=? AND bill_id=?", (city, bill_id)
        ).fetchone()
        if existing:
            return False
        conn.execute("""
            INSERT INTO legislation
                (city, source, bill_id, title, description, status, introduced_date,
                 url, keyword_matches, raw_json, first_seen_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            city, source, bill_id, title, description, status, introduced_date,
            url, json.dumps(keyword_matches), json.dumps(raw), _now()
        ))
        return True


# ── Alert dedup ───────────────────────────────────────────────────────────────

def already_alerted(alert_key: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM alerts_sent WHERE alert_key=?", (alert_key,)
        ).fetchone()
        return row is not None


def record_alert(alert_key: str, alert_type: str, city: str, summary: str):
    with get_conn() as conn:
        try:
            conn.execute(
                "INSERT INTO alerts_sent (alert_key, alert_type, city, summary, sent_at) VALUES (?, ?, ?, ?, ?)",
                (alert_key, alert_type, city, summary, _now())
            )
        except sqlite3.IntegrityError:
            pass  # Already recorded



def upsert_austin_license(record: dict) -> dict:
    conn = get_conn()
    license_id = record.get("license_id")
    status = (record.get("status") or "").lower()
    is_revoked = any(s in status for s in ["revoked", "expired", "inactive", "cancelled"])
    existing = conn.execute(
        "SELECT status FROM austin_licenses WHERE license_id = ?", (license_id,)
    ).fetchone()
    now = datetime.now(timezone.utc).isoformat()
    if existing is None:
        conn.execute(
            """INSERT INTO austin_licenses
               (license_id, license_type, status, address, street_name, zip_code,
                neighborhood, council_district, owner_name, issued_date, expiry_date,
                first_seen, last_updated, raw_json)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (license_id, record.get("license_type"), record.get("status"),
             record.get("address"), record.get("street_name"), record.get("zip_code"),
             record.get("neighborhood"), record.get("council_district"),
             record.get("owner_name"), record.get("issued_date"), record.get("expiry_date"),
             now, now, str(record.get("raw", {})))
        )
        conn.execute("""
        CREATE TABLE IF NOT EXISTS scottsdale_licenses (
            license_id     TEXT PRIMARY KEY,
            address        TEXT,
            owner_name     TEXT,
            mgmt_company   TEXT,
            emerg_contact  TEXT,
            emerg_phone    TEXT,
            property_score TEXT,
            status         TEXT DEFAULT 'active',
            first_seen     TEXT,
            last_updated   TEXT,
            raw_json       TEXT
        )
    """)
        return {"is_new": True, "was_revoked": False}
    was_revoked = is_revoked and "revok" not in (existing["status"] or "").lower()
    conn.execute(
        """UPDATE austin_licenses
           SET status=?, license_type=?, address=?, street_name=?, zip_code=?,
               neighborhood=?, council_district=?, owner_name=?, issued_date=?,
               expiry_date=?, last_updated=?, raw_json=?
           WHERE license_id=?""",
        (record.get("status"), record.get("license_type"), record.get("address"),
         record.get("street_name"), record.get("zip_code"), record.get("neighborhood"),
         record.get("council_district"), record.get("owner_name"),
         record.get("issued_date"), record.get("expiry_date"),
         now, str(record.get("raw", {})), license_id)
    )
    conn.commit()
    return {"is_new": False, "was_revoked": was_revoked}


def get_austin_license_stats() -> dict:
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) FROM austin_licenses").fetchone()[0]
    active = conn.execute(
        "SELECT COUNT(*) FROM austin_licenses "
        "WHERE lower(status) NOT IN ('revoked','expired','inactive','cancelled')"
    ).fetchone()[0]
    by_type = conn.execute(
        "SELECT license_type, COUNT(*) as n FROM austin_licenses GROUP BY license_type"
    ).fetchall()
    return {
        "total": total,
        "active": active,
        "by_type": {row["license_type"]: row["n"] for row in by_type},
    }


def upsert_scottsdale_license(record: dict) -> dict:
    conn = get_conn()
    license_id = record.get("license_id")
    existing = conn.execute("SELECT license_id FROM scottsdale_licenses WHERE license_id = ?", (license_id,)).fetchone()
    now = datetime.now(timezone.utc).isoformat()
    if existing is None:
        conn.execute("INSERT INTO scottsdale_licenses (license_id, address, owner_name, mgmt_company, emerg_contact, emerg_phone, property_score, status, first_seen, last_updated, raw_json) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (license_id, record.get("address"), record.get("owner_name"), record.get("mgmt_company"), record.get("emerg_contact"), record.get("emerg_phone"), record.get("property_score"), record.get("status","active"), now, now, str(record.get("raw",{}))))
        conn.commit()
        return {"is_new": True}
    conn.execute("UPDATE scottsdale_licenses SET address=?, owner_name=?, mgmt_company=?, emerg_contact=?, emerg_phone=?, property_score=?, last_updated=?, raw_json=? WHERE license_id=?",
        (record.get("address"), record.get("owner_name"), record.get("mgmt_company"), record.get("emerg_contact"), record.get("emerg_phone"), record.get("property_score"), now, str(record.get("raw",{})), license_id))
    conn.commit()
    return {"is_new": False}


def get_scottsdale_license_stats() -> dict:
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) FROM scottsdale_licenses").fetchone()[0]
    return {"total": total, "active": total}


def get_last_scottsdale_sync() -> str:
    conn = get_conn()
    try:
        row = conn.execute("SELECT MAX(last_updated) FROM scottsdale_licenses").fetchone()
        return row[0] if row and row[0] else None
    except Exception:
        return None
