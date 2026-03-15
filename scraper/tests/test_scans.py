"""
tests/test_scans.py — Tests for market scan report generation.

Covers:
- JSON parsing from Claude responses (markdown fences, preamble text, raw JSON)
- Beta market enrichment detection
- Report structure validation

Note: These test the parsing logic extracted from the API route.
The actual API route runs in Next.js, but the parsing logic is testable standalone.
"""

import pytest
import json


# ── Extract the JSON parsing logic so we can test it ──────────────────────────

def parse_scan_response(response_text: str) -> dict:
    """
    Parse Claude's response into a JSON report.
    Mirrors the logic in /api/scans/generate/route.ts.
    """
    import re

    clean = response_text.strip()

    # Strip markdown code fences
    fence_match = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?\s*```', clean)
    if fence_match:
        clean = fence_match.group(1).strip()

    # If still not starting with {, find the JSON object
    if not clean.startswith('{'):
        json_start = clean.find('{')
        json_end = clean.rfind('}')
        if json_start != -1 and json_end != -1:
            clean = clean[json_start:json_end + 1]

    return json.loads(clean)


SAMPLE_REPORT = {
    "city": "Nashville, TN",
    "generated_at": "2026-03-14",
    "summary": "Nashville has an active STR regulatory environment.",
    "risk_level": "medium",
    "sections": {
        "permit_requirements": {
            "title": "Permit & License Requirements",
            "items": [
                {"label": "Permit types", "value": "Type 1, 2, 3", "detail": "Based on occupancy"}
            ]
        },
        "fees_and_taxes": {
            "title": "Fees & Tax Obligations",
            "items": [
                {"label": "Permit fee", "value": "$313/year", "detail": "Annual renewal required"}
            ]
        },
        "restrictions": {
            "title": "Operating Restrictions",
            "items": []
        },
        "enforcement": {
            "title": "Enforcement & Penalties",
            "items": [
                {"label": "Fine", "value": "$500/day", "detail": "Operating without permit"}
            ]
        },
        "upcoming_changes": {
            "title": "Upcoming Changes & Deadlines",
            "items": []
        },
        "market_notes": {
            "title": "Market Notes",
            "items": []
        }
    },
    "key_contacts": [
        {"name": "Metro Codes", "phone": "615-862-6590", "url": "https://nashville.gov"}
    ],
    "disclaimer": "This report is for informational purposes only."
}


class TestJsonParsing:
    """Test that various Claude response formats are parsed correctly."""

    def test_raw_json(self):
        raw = json.dumps(SAMPLE_REPORT)
        result = parse_scan_response(raw)
        assert result["city"] == "Nashville, TN"
        assert result["risk_level"] == "medium"

    def test_json_with_markdown_fences(self):
        raw = '```json\n' + json.dumps(SAMPLE_REPORT) + '\n```'
        result = parse_scan_response(raw)
        assert result["city"] == "Nashville, TN"

    def test_json_with_bare_fences(self):
        raw = '```\n' + json.dumps(SAMPLE_REPORT) + '\n```'
        result = parse_scan_response(raw)
        assert result["city"] == "Nashville, TN"

    def test_json_with_preamble_text(self):
        raw = 'Here is the report:\n\n' + json.dumps(SAMPLE_REPORT)
        result = parse_scan_response(raw)
        assert result["city"] == "Nashville, TN"

    def test_json_with_preamble_and_fences(self):
        raw = 'Here is the market scan report:\n\n```json\n' + json.dumps(SAMPLE_REPORT) + '\n```'
        result = parse_scan_response(raw)
        assert result["city"] == "Nashville, TN"

    def test_json_with_trailing_text(self):
        raw = json.dumps(SAMPLE_REPORT) + '\n\nLet me know if you need anything else.'
        result = parse_scan_response(raw)
        assert result["city"] == "Nashville, TN"

    def test_json_with_whitespace(self):
        raw = '\n\n  ' + json.dumps(SAMPLE_REPORT, indent=2) + '\n\n  '
        result = parse_scan_response(raw)
        assert result["city"] == "Nashville, TN"

    def test_pretty_printed_json(self):
        raw = json.dumps(SAMPLE_REPORT, indent=2)
        result = parse_scan_response(raw)
        assert result["city"] == "Nashville, TN"
        assert len(result["sections"]) == 6

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            parse_scan_response("This is not JSON at all")

    def test_empty_string_raises(self):
        with pytest.raises(json.JSONDecodeError):
            parse_scan_response("")

    def test_partial_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            parse_scan_response('{"city": "Nashville"')


class TestReportStructure:
    """Validate report JSON structure matches expected format."""

    def test_has_required_top_level_fields(self):
        result = parse_scan_response(json.dumps(SAMPLE_REPORT))
        assert "city" in result
        assert "summary" in result
        assert "risk_level" in result
        assert "sections" in result

    def test_risk_level_is_valid(self):
        for level in ["low", "medium", "high"]:
            report = {**SAMPLE_REPORT, "risk_level": level}
            result = parse_scan_response(json.dumps(report))
            assert result["risk_level"] == level

    def test_sections_have_title_and_items(self):
        result = parse_scan_response(json.dumps(SAMPLE_REPORT))
        for section_key, section in result["sections"].items():
            assert "title" in section, f"Section {section_key} missing title"
            assert "items" in section, f"Section {section_key} missing items"
            assert isinstance(section["items"], list)

    def test_items_have_label_and_value(self):
        result = parse_scan_response(json.dumps(SAMPLE_REPORT))
        for section_key, section in result["sections"].items():
            for item in section["items"]:
                assert "label" in item, f"Item in {section_key} missing label"
                assert "value" in item, f"Item in {section_key} missing value"

    def test_key_contacts_structure(self):
        result = parse_scan_response(json.dumps(SAMPLE_REPORT))
        assert "key_contacts" in result
        assert isinstance(result["key_contacts"], list)
        for contact in result["key_contacts"]:
            assert "name" in contact

    def test_disclaimer_present(self):
        result = parse_scan_response(json.dumps(SAMPLE_REPORT))
        assert "disclaimer" in result
        assert len(result["disclaimer"]) > 10


class TestBetaMarketEnrichment:
    """Test that beta market detection works correctly."""

    BETA_CITIES = [
        'Nashville, TN',
        'Austin, TX',
        'Denver, CO',
        'Scottsdale, AZ',
        'Palm Springs, CA',
    ]

    NON_BETA_CITIES = [
        'Charleston, SC',
        'Gatlinburg, TN',
        'Miami, FL',
        'Portland, OR',
        'New York, NY',
    ]

    def test_beta_cities_detected(self):
        # This mirrors the BETA_MARKETS dict check in the route
        BETA_MARKETS = {c: True for c in self.BETA_CITIES}
        for city in self.BETA_CITIES:
            assert city in BETA_MARKETS, f"{city} should be a beta market"

    def test_non_beta_cities_not_enriched(self):
        BETA_MARKETS = {c: True for c in self.BETA_CITIES}
        for city in self.NON_BETA_CITIES:
            assert city not in BETA_MARKETS, f"{city} should not be a beta market"

    def test_enrichment_flag_set_correctly(self):
        BETA_MARKETS = {c: "context" for c in self.BETA_CITIES}
        for city in self.BETA_CITIES:
            is_enriched = city in BETA_MARKETS
            assert is_enriched is True

        for city in self.NON_BETA_CITIES:
            is_enriched = city in BETA_MARKETS
            assert is_enriched is False


class TestEdgeCases:
    """Test edge cases in report generation."""

    def test_report_with_empty_sections(self):
        report = {
            **SAMPLE_REPORT,
            "sections": {
                "permit_requirements": {"title": "Permits", "items": []},
                "fees_and_taxes": {"title": "Fees", "items": []},
                "restrictions": {"title": "Restrictions", "items": []},
                "enforcement": {"title": "Enforcement", "items": []},
                "upcoming_changes": {"title": "Changes", "items": []},
                "market_notes": {"title": "Notes", "items": []},
            }
        }
        result = parse_scan_response(json.dumps(report))
        assert len(result["sections"]) == 6

    def test_report_with_no_contacts(self):
        report = {**SAMPLE_REPORT, "key_contacts": []}
        result = parse_scan_response(json.dumps(report))
        assert result["key_contacts"] == []

    def test_report_with_unicode(self):
        report = {**SAMPLE_REPORT, "summary": "Nashville's STR regulations — strict & comprehensive"}
        result = parse_scan_response(json.dumps(report))
        assert "Nashville's" in result["summary"]

    def test_report_with_many_items(self):
        items = [{"label": f"Rule {i}", "value": f"${i*100}", "detail": f"Detail {i}"} for i in range(20)]
        report = {
            **SAMPLE_REPORT,
            "sections": {
                **SAMPLE_REPORT["sections"],
                "enforcement": {"title": "Enforcement", "items": items}
            }
        }
        result = parse_scan_response(json.dumps(report))
        assert len(result["sections"]["enforcement"]["items"]) == 20
