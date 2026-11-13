"""
tests/conftest.py — Pytest configuration for STRWatch scraper tests.

Adds the scraper root to sys.path so imports like
`from scrapers.keywords import matches_keywords` work.
"""

import sys
import os

# Add the scraper root directory to path
# Assumes tests/ is at the same level as scrapers/, db/, alerts/
SCRAPER_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SCRAPER_ROOT not in sys.path:
    sys.path.insert(0, SCRAPER_ROOT)

# alerts.router / alerts.reminders raise at import when SUPABASE_URL is unset.
# Tests mock every HTTP call, so any placeholder value will do.
os.environ.setdefault("SUPABASE_URL", "https://test-project.supabase.co")
# router.get_users_for_city / get_user_email short-circuit to [] / None when
# these are unset, which makes the mocked-HTTP tests fail for the wrong reason.
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("CLERK_SECRET_KEY", "sk_test_placeholder")
