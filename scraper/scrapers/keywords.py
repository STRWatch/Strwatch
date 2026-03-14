"""
scrapers/keywords.py — Shared keyword matching for all STRWatch scrapers.

Single source of truth for STR keyword detection. Uses word-boundary regex
to avoid false positives (e.g. "STR" matching "construct" or "district").

Usage:
    from scrapers.keywords import matches_keywords
    hits = matches_keywords("New STR overlay district ordinance", config.STR_KEYWORDS)
    # → ["STR", "overlay district"]
"""

import re
from typing import List


def matches_keywords(text: str, keywords: List[str]) -> List[str]:
    """
    Return list of keywords found in text using whole-word matching.

    Uses \\b word boundaries so "STR" won't match "construct" or "district".
    Case-insensitive. Returns the original keyword casing from the list.

    Args:
        text: The text to search through.
        keywords: List of keywords/phrases to look for.

    Returns:
        List of matched keywords (original casing preserved).
    """
    if not text:
        return []
    text_lower = text.lower()
    matches = []
    for kw in keywords:
        pattern = r'\b' + re.escape(kw.lower()) + r'\b'
        if re.search(pattern, text_lower):
            matches.append(kw)
    return matches
