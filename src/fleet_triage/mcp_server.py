"""Model Context Protocol server — "talk to your fleet".

This exposes the deterministic engine as MCP tools. It needs **no API key**: the
server only returns structured data; the user's Claude client (Claude Desktop,
Claude Code, etc.) supplies the reasoning and calls these tools for ground truth.

Run it:
    fleet-triage-mcp                 # stdio server (what a Claude client launches)
    python -m fleet_triage.mcp_server

Point it at custom data/policy with env vars:
    FLEET_TRIAGE_DATA=/path/fleet.json  FLEET_TRIAGE_RULESET=/path/ruleset.yaml
"""

from __future__ import annotations

import os
from dataclasses import asdict
from datetime import datetime
from functools import lru_cache

from mcp.server.fastmcp import FastMCP

from .engine import analyze
from .loader import DEFAULT_DATA_PATH, load_fleet
from .ruleset import DEFAULT_RULESET_PATH, load_ruleset
from .runbooks import runbook_for_cluster, runbook_for_device, suggest_remediation as _steps_for_control

mcp = FastMCP("fleet-triage")

_DATA_PATH = os.environ.get("FLEET_TRIAGE_DATA", str(DEFAULT_DATA_PATH))
_RULESET_PATH = os.environ.get("FLEET_TRIAGE_RULESET", str(DEFAULT_RULESET_PATH))


def _parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


@lru_cache(maxsize=1)
def _state():
    """Load + analyze once; every tool reads from this cached snapshot."""
    from .scoring import evaluate

    data = load_fleet(_DATA_PATH)
    rs = load_ruleset(_RULESET_PATH)
    report = analyze(data, rs)
    reference = _parse_iso(report.generated_at)
    breakdowns = {ep.device_id: evaluate(ep, rs, reference) for ep in data.endpoints}
    return data, rs, report, breakdowns


@mcp.tool()
def get_fleet_health() -> dict:
    """Return the overall fleet-health summary: totals, compliance %, severity
    counts, and compliance broken down by role and by location."""
    _, _, report, _ = _state()
    return {
        "generated_at": report.generated_at,
        "total": report.total,
        "compliant": report.compliant,
        "compliance_pct": report.compliance_pct,
        "severity_counts": report.severity_counts,
        "by_role": report.by_role,
        "by_location": report.by_location,
    }


@mcp.tool()
def list_endpoints(role: str | None = None, location: str | None = None,
                   min_risk: int = 0, limit: int = 25) -> list[dict]:
    """List endpoints, optionally filtered by role, location, and minimum risk
    score. Returns a compact summary per device, highest risk first."""
    _, _, _, breakdowns = _state()
    rows = []
    for b in breakdowns.values():
        if role and b.role != role:
            continue
        if location and b.location != location:
            continue
        if b.risk < min_risk:
            continue
        dom = b.dominant
        rows.append({
            "device_id": b.device_id, "hostname": b.hostname, "role": b.role,
            "location": b.location, "risk": b.risk, "band": b.band,
            "compliant": b.compliant, "top_issue": dom.detail if dom else None,
        })
    rows.sort(key=lambda r: r["risk"], reverse=True)
    return rows[:limit]


@mcp.tool()
def get_compliance(device_id: str) -> dict:
    """Return the full compliance breakdown for one device: its risk score,
    band, compliance verdict, and every failing control with point values."""
    _, _, _, breakdowns = _state()
    b = breakdowns.get(device_id)
    if b is None:
        return {"error": f"device {device_id!r} not found"}
    return asdict(b)


@mcp.tool()
def get_clusters(min_count: int = 2) -> list[dict]:
    """Return root-cause clusters: groups of at-risk devices sharing a dominant
    fault, with the role/location they correlate to and a runbook key."""
    _, _, report, _ = _state()
    return [asdict(c) for c in report.clusters if c.affected_count >= min_count]


@mcp.tool()
def suggest_remediation(device_id: str | None = None, cluster_key: str | None = None) -> dict:
    """Suggest concrete remediation steps for a device (by id) or a cluster
    (by runbook key). Steps are deterministic and derived from the findings."""
    _, _, report, breakdowns = _state()
    if device_id:
        b = breakdowns.get(device_id)
        if b is None:
            return {"error": f"device {device_id!r} not found"}
        controls = [f.control for f in sorted(b.factors, key=lambda x: x.points, reverse=True)]
        steps: list[str] = []
        for c in controls:
            steps += [s for s in _steps_for_control(c) if s not in steps]
        return {"target": device_id, "controls": controls, "steps": steps}
    if cluster_key:
        cl = next((c for c in report.clusters if c.runbook_key == cluster_key), None)
        if cl is None:
            return {"error": f"no cluster with key {cluster_key!r}",
                    "available": [c.runbook_key for c in report.clusters]}
        return {"target": cluster_key, "root_cause": cl.root_cause,
                "steps": _steps_for_control(cl.root_cause)}
    return {"error": "provide device_id or cluster_key"}


@mcp.tool()
def generate_runbook(cluster_key: str | None = None, device_id: str | None = None) -> str:
    """Generate a Confluence-style remediation runbook (markdown) for a cluster
    (by runbook key) or a single device (by id). The client's model can enrich
    the returned scaffold."""
    _, _, report, breakdowns = _state()
    if cluster_key:
        cl = next((c for c in report.clusters if c.runbook_key == cluster_key), None)
        if cl is None:
            return f"No cluster with key '{cluster_key}'. Available: " + ", ".join(
                c.runbook_key for c in report.clusters)
        return runbook_for_cluster(cl, report)
    if device_id:
        b = breakdowns.get(device_id)
        if b is None:
            return f"Device '{device_id}' not found."
        return runbook_for_device(b)
    return "Provide cluster_key or device_id."


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
