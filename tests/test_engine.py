"""Golden-value tests on the committed, seeded fleet (data/fleet.json, seed 1337).

These pin the end-to-end behaviour so a regression in scoring, clustering, or the
generator is caught immediately. If you intentionally retune the ruleset or the
generator, regenerate the fleet and update these numbers.
"""

from fleet_triage.engine import analyze
from fleet_triage.loader import load_fleet
from fleet_triage.ruleset import load_ruleset


def _report():
    return analyze(load_fleet(), load_ruleset())


def test_fleet_aggregates():
    r = _report()
    assert r.total == 200
    assert r.compliant == 156
    assert r.compliance_pct == 78.0
    assert r.severity_counts == {"healthy": 102, "low": 58, "medium": 36, "critical": 4}
    assert len(r.at_risk) == 40


def test_clusters_reproduce_planted_stories():
    r = _report()
    by_key = {c.runbook_key: c for c in r.clusters}
    assert by_key["patch-drift-render-nodes"].affected_count == 18
    assert by_key["encryption-off-edit-bays"].affected_count == 9
    assert by_key["stale-checkin-booths"].affected_count == 6
    # The encryption story is perfectly correlated to ATX edit-bays.
    assert "role=edit-bay (9/9)" in by_key["encryption-off-edit-bays"].correlate
    assert "location=ATX (9/9)" in by_key["encryption-off-edit-bays"].correlate


def test_at_risk_sorted_descending():
    r = _report()
    risks = [b.risk for b in r.at_risk]
    assert risks == sorted(risks, reverse=True)
    assert all(b.risk >= 40 for b in r.at_risk)


def test_report_json_roundtrips():
    import json

    r = _report()
    blob = json.dumps(r.to_dict())
    parsed = json.loads(blob)
    assert parsed["total"] == 200
    assert parsed["clusters"][0]["runbook_key"] == "patch-drift-render-nodes"
