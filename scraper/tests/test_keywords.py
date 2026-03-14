"""
tests/test_keywords.py — Tests for the shared keyword matching utility.

Covers:
- Word boundary matching (the main bug fix)
- Case insensitivity
- Multi-word phrase matching
- Empty/None input handling
- Real-world false positive scenarios from Nashville scraper
"""

import pytest
from scrapers.keywords import matches_keywords


# ── The STR keywords list from config.py ─────────────────────────────────────
STR_KEYWORDS = [
    "short-term rental", "short term rental", "STR", "STRP",
    "vacation rental", "home sharing", "Airbnb", "VRBO",
    "lodger's tax", "hotel occupancy", "permit cap", "overlay district",
    "non-owner occupied", "owner-occupied", "transient occupancy",
]


class TestWordBoundaryMatching:
    """The core bug fix: STR should NOT match substrings like construct, district."""

    def test_str_matches_standalone(self):
        assert "STR" in matches_keywords("New STR regulations announced", STR_KEYWORDS)

    def test_str_does_not_match_construct(self):
        assert "STR" not in matches_keywords("Construction of new building approved", STR_KEYWORDS)

    def test_str_does_not_match_district(self):
        assert "STR" not in matches_keywords("District 5 council meeting agenda", STR_KEYWORDS)

    def test_str_does_not_match_demonstrate(self):
        assert "STR" not in matches_keywords("Demonstrate compliance with building codes", STR_KEYWORDS)

    def test_str_does_not_match_restructure(self):
        assert "STR" not in matches_keywords("Restructure the zoning committee", STR_KEYWORDS)

    def test_str_matches_at_start_of_text(self):
        assert "STR" in matches_keywords("STR permit renewal deadline", STR_KEYWORDS)

    def test_str_matches_at_end_of_text(self):
        assert "STR" in matches_keywords("New regulations for STR", STR_KEYWORDS)

    def test_str_matches_with_punctuation(self):
        assert "STR" in matches_keywords("All STR-related items on agenda", STR_KEYWORDS)

    def test_str_matches_in_parentheses(self):
        assert "STR" in matches_keywords("Short-term rental (STR) ordinance", STR_KEYWORDS)


class TestPhraseMatching:
    """Multi-word keywords should match as complete phrases."""

    def test_short_term_rental_hyphenated(self):
        assert "short-term rental" in matches_keywords(
            "New short-term rental ordinance passed", STR_KEYWORDS)

    def test_short_term_rental_no_hyphen(self):
        assert "short term rental" in matches_keywords(
            "Short term rental regulations updated", STR_KEYWORDS)

    def test_overlay_district(self):
        assert "overlay district" in matches_keywords(
            "STR overlay district expansion proposed", STR_KEYWORDS)

    def test_overlay_district_not_just_district(self):
        # "district" alone should not match — only "overlay district" as a phrase
        result = matches_keywords("District 5 council meeting", STR_KEYWORDS)
        assert "overlay district" not in result

    def test_vacation_rental(self):
        assert "vacation rental" in matches_keywords(
            "Vacation rental density cap reached", STR_KEYWORDS)

    def test_transient_occupancy(self):
        assert "transient occupancy" in matches_keywords(
            "Transient occupancy tax rate increased to 12%", STR_KEYWORDS)


class TestCaseInsensitivity:
    """Matching should be case-insensitive."""

    def test_lowercase(self):
        assert "STR" in matches_keywords("str permits required", STR_KEYWORDS)

    def test_uppercase(self):
        assert "Airbnb" in matches_keywords("AIRBNB listings must comply", STR_KEYWORDS)

    def test_mixed_case(self):
        assert "VRBO" in matches_keywords("Vrbo and Airbnb platforms", STR_KEYWORDS)


class TestEdgeCases:
    """Empty inputs, None, and boundary conditions."""

    def test_empty_text(self):
        assert matches_keywords("", STR_KEYWORDS) == []

    def test_none_text(self):
        # None should not crash, should return empty
        assert matches_keywords(None, STR_KEYWORDS) == []

    def test_empty_keywords(self):
        assert matches_keywords("Some text about STR", []) == []

    def test_no_matches(self):
        assert matches_keywords("Budget meeting for parks department", STR_KEYWORDS) == []

    def test_multiple_matches(self):
        result = matches_keywords(
            "STR overlay district and vacation rental permit cap discussion", STR_KEYWORDS)
        assert "STR" in result
        assert "overlay district" in result
        assert "vacation rental" in result
        assert "permit cap" in result

    def test_preserves_original_keyword_casing(self):
        """The returned keywords should use the casing from the keyword list, not the text."""
        result = matches_keywords("str permits", STR_KEYWORDS)
        assert "STR" in result  # Original casing from keyword list


class TestRealWorldNashvilleText:
    """Test against real Nashville council item titles that caused false positives."""

    def test_construction_permit_no_match(self):
        title = "An ordinance approving construction permits for district 12 infrastructure"
        result = matches_keywords(title, STR_KEYWORDS)
        assert result == [], f"False positive: {result}"

    def test_redistricting_no_match(self):
        title = "Resolution to demonstrate support for redistricting commission"
        result = matches_keywords(title, STR_KEYWORDS)
        assert result == [], f"False positive: {result}"

    def test_real_str_bill_matches(self):
        title = "An ordinance amending Nashville STR permit requirements for non-owner occupied properties"
        result = matches_keywords(title, STR_KEYWORDS)
        assert "STR" in result
        assert "non-owner occupied" in result

    def test_real_str_bill_with_strp(self):
        title = "Resolution regarding STRP overlay district density caps in residential zones"
        result = matches_keywords(title, STR_KEYWORDS)
        assert "STRP" in result
        assert "overlay district" in result
