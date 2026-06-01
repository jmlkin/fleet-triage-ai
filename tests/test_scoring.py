from fleet_triage.scoring import days_since_checkin, evaluate, months_behind

from .conftest import make_endpoint


def test_months_behind():
    assert months_behind("2026-02", "2026-06") == 4
    assert months_behind("2026-06", "2026-06") == 0
    assert months_behind("2025-12", "2026-06") == 6
    assert months_behind("2026-08", "2026-06") == 0  # never negative


def test_days_since_checkin(as_of):
    assert days_since_checkin("2026-06-01T00:00:00Z", as_of) == 0
    assert days_since_checkin("2026-05-02T00:00:00Z", as_of) == 30


def test_healthy_endpoint_scores_zero(rs, as_of):
    rb = evaluate(make_endpoint(), rs, as_of)
    assert rb.risk == 0
    assert rb.band == "healthy"
    assert rb.compliant is True
    assert rb.factors == []


def test_patch_drift_render_node(rs, as_of):
    # 4 months behind: 4*10 capped at 40, x1.2 role multiplier = 48.
    rb = evaluate(make_endpoint(installed_patch_level="2026-02"), rs, as_of)
    assert rb.risk == 48
    assert rb.band == "medium"
    assert rb.compliant is False
    assert rb.dominant.control == "patch_drift"


def test_encryption_off_edit_bay(rs, as_of):
    # encryption_off=35, x1.2 (edit-bay) = 42.
    rb = evaluate(make_endpoint(role="edit-bay", disk_encryption="off"), rs, as_of)
    assert rb.risk == 42
    assert rb.compliant is False
    assert rb.dominant.control == "encryption_off"


def test_stacked_faults_capped_at_100(rs, as_of):
    rb = evaluate(
        make_endpoint(
            installed_patch_level="2026-01",
            disk_encryption="off",
            mdm_enrolled=False,
            patch_ring="unmanaged",
            edr_agent_healthy=False,
        ),
        rs,
        as_of,
    )
    assert rb.risk == 100
    assert rb.band == "critical"
