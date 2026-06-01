"""Tests for the MCP tool layer.

We import the underlying tool callables and assert they return well-typed
payloads over the committed fleet. (No Claude client or network involved — the
server is pure data.) Skips cleanly if the optional `mcp` extra isn't installed.
"""

import pytest

pytest.importorskip("mcp", reason="install with `.[mcp]` to run MCP tests")

from fleet_triage import mcp_server as srv


@pytest.fixture(autouse=True)
def _clear_cache():
    srv._state.cache_clear()
    yield
    srv._state.cache_clear()


def test_get_fleet_health():
    h = srv.get_fleet_health()
    assert h["total"] == 200
    assert h["compliance_pct"] == 78.0
    assert set(h["severity_counts"]) == {"healthy", "low", "medium", "critical"}
    assert "render-node" in h["by_role"]


def test_list_endpoints_filters():
    booths = srv.list_endpoints(role="recording-booth", min_risk=40)
    assert booths, "expected at-risk booths"
    assert all(r["role"] == "recording-booth" and r["risk"] >= 40 for r in booths)
    # sorted descending
    assert [r["risk"] for r in booths] == sorted((r["risk"] for r in booths), reverse=True)


def test_get_compliance_and_missing():
    health = srv.get_fleet_health()  # noqa: F841 - warms cache
    any_id = srv.list_endpoints(min_risk=40, limit=1)[0]["device_id"]
    detail = srv.get_compliance(any_id)
    assert detail["device_id"] == any_id
    assert "factors" in detail
    assert "error" in srv.get_compliance("FLT-9999")


def test_get_clusters_keys():
    keys = {c["runbook_key"] for c in srv.get_clusters()}
    assert {"patch-drift-render-nodes", "encryption-off-edit-bays", "stale-checkin-booths"} <= keys


def test_generate_runbook_markdown():
    md = srv.generate_runbook(cluster_key="encryption-off-edit-bays")
    assert md.startswith("# Remediation Runbook")
    assert "## Remediation steps" in md
    assert "No cluster" in srv.generate_runbook(cluster_key="does-not-exist")


def test_suggest_remediation_cluster():
    out = srv.suggest_remediation(cluster_key="stale-checkin-booths")
    assert out["root_cause"] == "stale_checkin"
    assert len(out["steps"]) >= 1
