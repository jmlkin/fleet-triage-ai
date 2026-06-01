"""The single public analysis seam.

Both the CLI and the MCP server call `analyze()` — there is no scoring logic
anywhere else, so the terminal report, the JSON output, and the "talk to your
fleet" MCP tools can never disagree.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .clustering import build_clusters
from .models import FleetData, FleetReport, RiskBreakdown
from .ruleset import Ruleset
from .scoring import evaluate


def _parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _group(breakdowns: list[RiskBreakdown], key: str) -> dict:
    out: dict[str, dict] = {}
    for b in breakdowns:
        bucket = out.setdefault(getattr(b, key), {"total": 0, "compliant": 0})
        bucket["total"] += 1
        bucket["compliant"] += int(b.compliant)
    for bucket in out.values():
        bucket["compliance_pct"] = round(100 * bucket["compliant"] / bucket["total"], 1)
    return dict(sorted(out.items(), key=lambda kv: kv[1]["compliance_pct"]))


def analyze(data: FleetData, ruleset: Ruleset, as_of: str | None = None) -> FleetReport:
    """Score every device, aggregate, and cluster the at-risk set."""
    reference = _parse_iso(as_of or data.as_of or datetime.now(timezone.utc).isoformat())

    breakdowns = [evaluate(ep, ruleset, reference) for ep in data.endpoints]
    total = len(breakdowns)
    compliant = sum(b.compliant for b in breakdowns)

    severity_counts = {"healthy": 0, "low": 0, "medium": 0, "critical": 0}
    for b in breakdowns:
        severity_counts[b.band] += 1

    at_risk = sorted(
        (b for b in breakdowns if b.risk >= ruleset.at_risk_threshold),
        key=lambda b: b.risk,
        reverse=True,
    )

    return FleetReport(
        generated_at=reference.isoformat(),
        total=total,
        compliant=compliant,
        compliance_pct=round(100 * compliant / total, 1) if total else 0.0,
        severity_counts=severity_counts,
        by_role=_group(breakdowns, "role"),
        by_location=_group(breakdowns, "location"),
        at_risk=at_risk,
        clusters=build_clusters(at_risk),
    )
