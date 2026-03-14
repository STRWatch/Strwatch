"""
config.py — Central settings for STRWatch scraper.
All env vars loaded here. Import this everywhere.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "strwatch.db"

# ── Alerts ────────────────────────────────────────────────────────────────────
ALERT_EMAIL = os.getenv("ALERT_EMAIL", "")
ALERT_PHONE = os.getenv("ALERT_PHONE", "")

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM = os.getenv("RESEND_FROM", "alerts@strwatch.io")

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM = os.getenv("TWILIO_FROM", "")

# ── Supabase (optional) ───────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_KEY)

# ── Denver SODA API ───────────────────────────────────────────────────────────
DENVER_SODA_ENDPOINT = "https://data.colorado.gov/resource/f3vc-vat3.json"
DENVER_SODA_LIMIT = 1000  # records per page

# ── Nashville Legistar ────────────────────────────────────────────────────────
NASHVILLE_LEGISTAR_BASE = "https://webapi.legistar.com/v1/nashville"
NASHVILLE_LEGISTAR_RSS = "https://nashville.legistar.com/Feed.ashx?M=Calendar&ID=Nashville&GUID=&Mode=All&Title=Nashville+Metro+Council"

# ── Austin ────────────────────────────────────────────────────────────────────
AUSTIN_STR_PAGE = "https://www.austintexas.gov/department/short-term-rentals"
AUSTIN_COUNCIL_AGENDA_BASE = "https://www.austintexas.gov/department/city-council/2026/2026_council_index.htm"

# ── STR keywords to watch for in legislation text ────────────────────────────
STR_KEYWORDS = [
    "short-term rental", "short term rental", "STR", "STRP",
    "vacation rental", "home sharing", "Airbnb", "VRBO",
    "lodger's tax", "hotel occupancy", "permit cap", "overlay district",
    "non-owner occupied", "owner-occupied", "transient occupancy",
]

# ── Monitored pages (generic hash watcher) ───────────────────────────────────
WATCHED_PAGES = [
    {
        "name": "Nashville — STRP Permit Page",
        "url": "https://www.nashville.gov/departments/codes/short-term-rentals",
        "city": "Nashville",
        "priority": "high",
    },
    {
        "name": "Nashville — Planning Commission",
        "url": "https://www.nashville.gov/departments/planning/boards/planning-commission",
        "city": "Nashville",
        "priority": "medium",
    },
    {
        "name": "Austin — STR Official Page",
        "url": "https://www.austintexas.gov/department/short-term-rentals",
        "city": "Austin",
        "priority": "high",
    },
    {
        "name": "Austin — Operating Licensing",
        "url": "https://www.austintexas.gov/page/operating-licensing",
        "city": "Austin",
        "priority": "high",
    },
    {
        "name": "Denver — STR Official Page",
        "url": "https://denvergov.org/Government/Agencies-Departments-Offices/Agencies-Departments-Offices-Directory/Business-Licensing/Business-licenses/Short-term-rentals",
        "city": "Denver",
        "priority": "high",
    },
    {
        "name": "Denver — STR Laws & Rules",
        "url": "https://www.denvergov.org/Government/Agencies-Departments-Offices/Agencies-Departments-Offices-Directory/Business-Licensing/Business-licenses/Short-term-rentals/Short-term-rentals-laws-rules-regulations",
        "city": "Denver",
        "priority": "high",
    },
]

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
