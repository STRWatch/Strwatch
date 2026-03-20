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

# ── New Orleans ───────────────────────────────────────────────────────────────
NOLA_LEGISTAR_BASE = "https://webapi.legistar.com/v1/cityofno"
NOLA_SODA_ENDPOINT = "https://data.nola.gov/resource/2ei9-wqw2.json"
NOLA_SODA_LIMIT = 1000

# ── San Diego ─────────────────────────────────────────────────────────────────
SANDIEGO_STRO_CSV = "https://seshat.datasd.org/stro/stro_licenses_datasd.csv"

# ── Indianapolis ──────────────────────────────────────────────────────────────
# NOTE: Indianapolis has Legistar software but the public API is not enabled.
# Monitoring is done via page watching (indy.gov + Municode Meetings portal).
# See scrapers/indianapolis_web.py

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
    {
        "name": "NOLA — STR Administration",
        "url": "https://www.nola.gov/short-term-rentals/",
        "city": "New Orleans, LA",
        "priority": "high",
    },
    {
        "name": "NOLA — STR Registry",
        "url": "https://nola.gov/next/short-term-rental-administration/topics/registry-of-short-term-rentals/",
        "city": "New Orleans, LA",
        "priority": "medium",
    },
    {
        "name": "San Diego — STRO Regulations",
        "url": "https://www.sandiego.gov/treasurer/short-term-residential-occupancy",
        "city": "San Diego, CA",
        "priority": "high",
    },
    {
        "name": "Indianapolis — STR Registration",
        "url": "https://www.indy.gov/activity/short-term-rental-registration",
        "city": "Indianapolis",
        "priority": "high",
    },
    {
        "name": "Indianapolis — DBNS Permits & Licensing",
        "url": "https://www.indy.gov/agency/department-of-business-and-neighborhood-services",
        "city": "Indianapolis",
        "priority": "medium",
    },
    {
        "name": "Indianapolis — Marion County Innkeeper's Tax",
        "url": "https://www.indy.gov/activity/innkeepers-tax",
        "city": "Indianapolis",
        "priority": "medium",
    },
    {
        "name": "Indianapolis — City-County Council Proposals",
        "url": "https://www.indy.gov/activity/city-county-council-proposals",
        "city": "Indianapolis",
        "priority": "high",
    },
    {
        "name": "Indianapolis — Council Meeting Agendas",
        "url": "https://www.indy.gov/activity/council-meeting-agendas",
        "city": "Indianapolis",
        "priority": "high",
    },
    {
        "name": "Indianapolis — Municode Meetings Portal",
        "url": "https://indianapolis-in.municodemeetings.com/",
        "city": "Indianapolis",
        "priority": "medium",
    },
    {
        "name": "Indianapolis — DMD Meetings (zoning/planning)",
        "url": "https://indianapolis-in.municodemeetings.com/DMDmeetings",
        "city": "Indianapolis",
        "priority": "high",
    },
]

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
