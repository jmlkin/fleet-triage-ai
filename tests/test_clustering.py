from fleet_triage.clustering import build_clusters
from fleet_triage.models import RiskBreakdown, RiskFactor


def _rb(device_id, role, location, control, points):
    return RiskBreakdown(
        device_id=device_id, hostname=f"{role}-{location.lower()}", role=role,
        location=location, risk=points, band="medium", compliant=False,
        factors=[RiskFactor(control, points, "detail")],
    )


def test_groups_by_dominant_control_and_finds_correlate():
    at_risk = [
        _rb("FLT-1", "edit-bay", "ATX", "encryption_off", 42),
        _rb("FLT-2", "edit-bay", "ATX", "encryption_off", 42),
        _rb("FLT-3", "edit-bay", "ATX", "encryption_off", 42),
        _rb("FLT-4", "render-node", "SEA", "patch_drift", 48),
        _rb("FLT-5", "render-node", "SEA", "patch_drift", 48),
    ]
    clusters = build_clusters(at_risk, min_count=2)
    keys = {c.runbook_key for c in clusters}
    assert "encryption-off-edit-bays" in keys
    assert "patch-drift-render-nodes" in keys

    enc = next(c for c in clusters if c.runbook_key == "encryption-off-edit-bays")
    assert enc.affected_count == 3
    assert "role=edit-bay (3/3)" in enc.correlate
    assert "location=ATX (3/3)" in enc.correlate


def test_min_count_filters_singletons():
    at_risk = [_rb("FLT-9", "laptop", "REMOTE", "firewall_off", 10)]
    assert build_clusters(at_risk, min_count=2) == []
