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
