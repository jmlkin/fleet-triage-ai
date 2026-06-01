"""Optional bring-your-own-key AI layer (Anthropic Python SDK).

This is the ONLY module that talks to a paid API, and it is entirely optional:
- `anthropic` is imported lazily, so the core tool installs and runs without it.
- Nothing here executes unless ANTHROPIC_API_KEY is set (`has_key()` gates it).
- Callers wrap these functions in try/except and fall back to committed samples,
  so the demo never crashes on the AI path.

Model + caching choices follow current Anthropic guidance: latest Claude model,
a stable system prompt marked with `cache_control` so repeated calls in one run
(summary + several runbooks) reuse the cached prefix.
"""

from __future__ import annotations

import json
import os

from .models import FleetReport

# Latest Claude model (see Anthropic model catalog). Opus uses adaptive thinking
# only; we leave thinking off here — a fleet summary is light, and that keeps the
# call fast and cheap for a BYO-key user.
MODEL = "claude-opus-4-8"

_SYSTEM_PROMPT = (
    "You are an endpoint-operations analyst writing for an IT/SRE leadership audience. "
    "You are given a JSON fleet-health report produced by a deterministic engine that "
    "scores managed endpoints against a compliance baseline and clusters at-risk devices "
    "by root cause. Write a crisp executive summary in Markdown.\n\n"
    "Requirements:\n"
    "- Lead with one sentence on overall fleet posture (compliance %, severity mix).\n"
    "- Call out the top root-cause clusters by name, with counts and the role/location "
    "they correlate to, and explain the likely systemic cause in plain language.\n"
    "- End with a short, prioritized 'Recommended actions' list (3-5 bullets).\n"
    "- Be specific and quantitative; never invent data not present in the report.\n"
    "- No preamble, no 'Here is' — start directly with the summary. Keep it under 250 words."
)


def has_key() -> bool:
    """True if a usable API key is present in the environment."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _compact(report: FleetReport) -> dict:
    """Trim the report to the fields worth sending — keeps the prompt small."""
    return {
        "total": report.total,
        "compliant": report.compliant,
        "compliance_pct": report.compliance_pct,
        "severity_counts": report.severity_counts,
        "by_role": report.by_role,
        "by_location": report.by_location,
        "clusters": [
            {
                "title": c.title,
                "root_cause": c.root_cause,
                "count": c.affected_count,
                "correlate": c.correlate,
            }
            for c in report.clusters
        ],
        "top_at_risk": [
            {"hostname": b.hostname, "role": b.role, "location": b.location,
             "risk": b.risk, "top_issue": (b.dominant.detail if b.dominant else None)}
            for b in report.at_risk[:10]
        ],
    }


def generate_executive_summary(report: FleetReport) -> str:
    """Generate a Markdown executive summary via the Anthropic API.

    Raises if `anthropic` is not installed or the call fails — callers are
    expected to catch and fall back to the committed sample.
    """
    import anthropic  # lazy: never imported unless this path actually runs

    client = anthropic.Anthropic()
    payload = json.dumps(_compact(report), indent=2)

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        # Stable instructions go in a cached system block; the volatile report
        # JSON goes in the user turn (after the cached prefix).
        system=[{"type": "text", "text": _SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{
            "role": "user",
            "content": f"Fleet-health report:\n\n```json\n{payload}\n```\n\nWrite the executive summary.",
        }],
    )
    return "".join(block.text for block in response.content if block.type == "text").strip()
