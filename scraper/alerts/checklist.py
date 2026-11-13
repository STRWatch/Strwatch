"""
alerts/checklist.py — AI compliance checklist generator.

Calls the Anthropic Messages API to generate a personalized, step-by-step
compliance checklist for each regulation change detected by scrapers.

Usage:
    from alerts.checklist import generate_checklist
    checklist = generate_checklist(
        city="Nashville",
        title="All STR operators must renew permits under new tiered system by April 15",
        keywords=["STR", "permit cap", "non-owner occupied"],
        source_url="https://nashville.legistar.com/...",
        alert_type="legislation",
    )
    # Returns: {"steps": [...], "deadline": "April 15, 2026", "raw_text": "..."}

Model: env ANTHROPIC_MODEL (default claude-sonnet-5-5), read per call.
"""

import os
import html
import json
import logging
from typing import Optional

# Imported at module level on purpose: a missing package must fail at import
# (caught by notify._generate_checklist_safe, alert still goes out without a
# checklist) rather than mid-send after the snapshot hash has been saved.
import nh3

log = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-sonnet-5-5"


def _model() -> str:
    """Model id, read from env at call time (ANTHROPIC_MODEL), not at import."""
    return os.getenv("ANTHROPIC_MODEL", "").strip() or DEFAULT_MODEL


def _api_key() -> str:
    return os.getenv("ANTHROPIC_API_KEY", "")


def generate_checklist(
    city: str,
    title: str,
    keywords: list,
    source_url: str = "",
    alert_type: str = "legislation",
    extra_context: str = "",
) -> Optional[dict]:
    """
    Generate an AI compliance checklist for a regulation change.

    Returns dict with:
        - steps: list of {"step": int, "action": str, "detail": str}
        - deadline: str or None
        - urgency: "high" | "medium" | "low"
        - summary: one-line plain-text summary
        - raw_text: full checklist as formatted text (for email)

    Returns None if API call fails or is not configured.
    """
    api_key = _api_key()
    if not api_key:
        log.warning("ANTHROPIC_API_KEY not set — skipping checklist generation")
        return None

    try:
        import anthropic
    except ImportError:
        log.error("anthropic package not installed — run: pip install anthropic")
        return None

    kw_str = ", ".join(keywords[:8]) if keywords else "general STR regulation"

    system_prompt = f"""You are a compliance advisor for short-term rental (STR) hosts in {city}.
Your job is to translate government regulation changes into clear, actionable steps that a property owner or manager can follow immediately.

Rules:
- Be specific: include exact fees, deadlines, form names, and office contacts when inferable from the regulation title and keywords.
- Be practical: tell the host exactly what to do, not just what the regulation says.
- If you don't know a specific detail (like an exact fee), say "verify with city" rather than guessing.
- Keep steps concise — one clear action per step.
- Include a deadline if one is mentioned or inferable.
- Assess urgency: "high" if there's a deadline within 60 days or risk of fines/delisting, "medium" if within 6 months, "low" otherwise.
- Respond ONLY with valid JSON, no markdown, no preamble."""

    user_prompt = f"""A regulation change was detected in {city}:

Title: {title}
Keywords matched: {kw_str}
Alert type: {alert_type}
Source: {source_url}
{f"Additional context: {extra_context}" if extra_context else ""}

Generate a compliance checklist as JSON with this exact structure:
{{
  "summary": "One sentence plain-text summary of what changed and what hosts need to do",
  "urgency": "high" or "medium" or "low",
  "deadline": "Specific date if known, or null",
  "steps": [
    {{
      "step": 1,
      "action": "Short action title (e.g., 'Check your permit type')",
      "detail": "Detailed instruction explaining exactly what to do and why"
    }}
  ]
}}

Generate 4-7 steps. Be specific to {city} STR regulations."""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=_model(),
            max_tokens=1500,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ],
        )

        # Extract text from response
        response_text = ""
        for block in message.content:
            if hasattr(block, "text"):
                response_text += block.text

        # Parse JSON response
        # Strip any markdown fences if present
        clean = response_text.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        clean = clean.strip()

        result = json.loads(clean)

        # Validate structure
        if "steps" not in result or not isinstance(result["steps"], list):
            log.error("Checklist response missing 'steps' array")
            return None

        # Generate formatted text version for email
        raw_text = _format_checklist_text(result, city, title)
        result["raw_text"] = raw_text

        log.info("Checklist generated for %s: %d steps, urgency=%s",
                 city, len(result["steps"]), result.get("urgency", "unknown"))

        return result

    except json.JSONDecodeError as e:
        log.error("Failed to parse checklist JSON: %s | Response: %s", e, response_text[:200])
        return None
    except anthropic.APIError as e:
        log.error("Anthropic API error: %s", e)
        return None
    except Exception as e:
        log.error("Checklist generation failed: %s", e)
        return None


def _format_checklist_text(result: dict, city: str, title: str) -> str:
    """Format checklist as plain text for email fallback."""
    lines = [
        f"COMPLIANCE CHECKLIST — {city}",
        f"{title}",
        "",
    ]
    if result.get("summary"):
        lines.append(result["summary"])
        lines.append("")
    if result.get("deadline"):
        lines.append(f"⚠ DEADLINE: {result['deadline']}")
        lines.append("")
    for step in result.get("steps", []):
        lines.append(f"  {step['step']}. {step['action']}")
        if step.get("detail"):
            lines.append(f"     {step['detail']}")
        lines.append("")
    return "\n".join(lines)


# HTML allowlist for checklist output. Mirrors the Next.js dashboard sanitizer
# exactly — the same string is stored in alerts.checklist and rendered there.
CHECKLIST_TAGS = {"ul", "ol", "li", "p", "strong", "em", "b", "i", "a", "br", "h3", "h4"}
CHECKLIST_ATTRIBUTES = {"a": {"href"}}
CHECKLIST_URL_SCHEMES = {"https", "http"}


def sanitize_checklist_html(raw_html: str) -> str:
    """nh3.clean() with the dashboard allowlist.

    Tags outside the allowlist are stripped (content kept), only href on <a>
    survives, and an href is kept only when it is an absolute http(s) URL —
    protocol-relative (//host) and other relative URLs are dropped.
    """
    if not raw_html:
        return ""
    return nh3.clean(
        raw_html,
        tags=CHECKLIST_TAGS,
        attributes=CHECKLIST_ATTRIBUTES,
        attribute_filter=_href_filter,
        url_schemes=CHECKLIST_URL_SCHEMES,
        link_rel=None,
    )


def _href_filter(tag: str, attr: str, value: str):
    """nh3 attribute_filter: keep href only for absolute http(s) URLs."""
    if tag == "a" and attr == "href":
        v = value.strip().lower()
        if v.startswith("https://") or v.startswith("http://"):
            return value
        return None
    return value


def _esc(value) -> str:
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def format_checklist_html(result: dict) -> str:
    """Format checklist as HTML for inclusion in alert emails and the dashboard.

    Only allowlisted tags are emitted (no div/table/style) so the output is
    identical before and after the dashboard's sanitizer. Every field here is
    LLM output and is escaped; the whole thing is then run through nh3.
    """
    if not result or not result.get("steps"):
        return ""

    urgency_labels = {"high": "Urgent", "medium": "Action needed", "low": "FYI"}
    label = urgency_labels.get(result.get("urgency", "medium"), "Action needed")

    parts = [f"<h4>AI COMPLIANCE CHECKLIST <em>({_esc(label)})</em></h4>"]

    if result.get("summary"):
        parts.append(f"<p>{_esc(result['summary'])}</p>")

    if result.get("deadline"):
        parts.append(f"<p><strong>⚠ DEADLINE: {_esc(result['deadline'])}</strong></p>")

    items = []
    for step in result["steps"]:
        if not isinstance(step, dict):
            continue
        action = _esc(step.get("action", ""))
        detail = _esc(step.get("detail", ""))
        item = f"<strong>{action}</strong>"
        if detail:
            item += f"<br>{detail}"
        items.append(f"<li>{item}</li>")
    parts.append("<ol>" + "".join(items) + "</ol>")

    parts.append("<p><em>Generated by STRWatch AI · Verify details with your local government</em></p>")

    return sanitize_checklist_html("\n".join(parts))


if __name__ == "__main__":
    """Test checklist generation."""
    logging.basicConfig(level=logging.DEBUG)

    test = generate_checklist(
        city="Nashville, TN",
        title="All STR operators must renew permits under new tiered system by April 15",
        keywords=["STR", "permit cap", "non-owner occupied"],
        source_url="https://nashville.legistar.com/test",
        alert_type="legislation",
    )

    if test:
        print("\n=== Checklist Generated ===")
        print(json.dumps(test, indent=2, default=str))
        print("\n=== Email HTML ===")
        print(format_checklist_html(test))
    else:
        print("Checklist generation failed — check ANTHROPIC_API_KEY")
