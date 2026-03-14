"""
alerts/checklist.py — AI compliance checklist generator.

Calls Claude Sonnet API to generate a personalized, step-by-step
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

Cost: ~$0.01–0.02 per checklist using Claude Sonnet 4.5.
"""

import os
import json
import logging
from typing import Optional

log = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = "claude-sonnet-4-5-20250929"


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
    if not ANTHROPIC_API_KEY:
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
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=MODEL,
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


def format_checklist_html(result: dict) -> str:
    """Format checklist as HTML for inclusion in alert emails."""
    if not result or not result.get("steps"):
        return ""

    urgency_colors = {
        "high": {"bg": "#fff0ee", "border": "#f7c8c8", "text": "#b84040", "label": "Urgent"},
        "medium": {"bg": "#fdf3e3", "border": "#f5d9a0", "text": "#b87d2d", "label": "Action needed"},
        "low": {"bg": "#e8f5ee", "border": "#c8ecd8", "text": "#2d7a4f", "label": "FYI"},
    }
    c = urgency_colors.get(result.get("urgency", "medium"), urgency_colors["medium"])

    steps_html = ""
    for step in result["steps"]:
        steps_html += f"""
        <tr>
          <td style="padding:10px 14px;vertical-align:top;width:32px;font-weight:700;color:#1a4d2e;font-size:14px;">{step['step']}.</td>
          <td style="padding:10px 14px;vertical-align:top;">
            <div style="font-weight:600;color:#0f1a0a;font-size:13px;margin-bottom:3px;">{step['action']}</div>
            <div style="color:#374530;font-size:12px;line-height:1.5;">{step.get('detail', '')}</div>
          </td>
        </tr>"""

    deadline_html = ""
    if result.get("deadline"):
        deadline_html = f"""
        <div style="background:#fdf3e3;border:1px solid #f5d9a0;border-radius:6px;padding:10px 14px;margin-bottom:16px;">
          <span style="font-size:12px;font-weight:700;color:#b87d2d;">⚠ DEADLINE: {result['deadline']}</span>
        </div>"""

    html = f"""
    <div style="margin-top:20px;border:1.5px solid #d8e8cf;border-radius:10px;overflow:hidden;">
      <div style="background:#1a4d2e;padding:12px 16px;display:flex;align-items:center;justify-content:space-between;">
        <span style="color:white;font-size:12px;font-weight:700;letter-spacing:0.5px;">AI COMPLIANCE CHECKLIST</span>
        <span style="background:{c['bg']};color:{c['text']};border:1px solid {c['border']};font-size:10px;padding:3px 10px;border-radius:100px;font-weight:600;">{c['label']}</span>
      </div>
      <div style="padding:16px;">
        {f'<p style="font-size:13px;color:#374530;margin:0 0 14px;line-height:1.55;">{result.get("summary", "")}</p>' if result.get("summary") else ""}
        {deadline_html}
        <table style="width:100%;border-collapse:collapse;">
          {steps_html}
        </table>
        <div style="margin-top:14px;padding-top:12px;border-top:1px solid #d8e8cf;">
          <span style="font-size:10px;color:#9aab90;letter-spacing:0.5px;">Generated by STRWatch AI · Verify details with your local government</span>
        </div>
      </div>
    </div>"""

    return html


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
