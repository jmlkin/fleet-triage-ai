from datetime import datetime, timezone

import pytest

from fleet_triage.models import Endpoint
from fleet_triage.ruleset import load_ruleset

AS_OF = datetime(2026, 6, 1, tzinfo=timezone.utc)


@pytest.fixture
def rs():
    return load_ruleset()


@pytest.fixture
def as_of():
    return AS_OF


def make_endpoint(**overrides) -> Endpoint:
    """A fully-compliant baseline endpoint; override fields to inject faults."""
    base = dict(
        device_id="T-0001",
        hostname="render-node-sea-001",
        role="render-node",
        location="SEA",
        os="Ubuntu",
        os_version="24.04",
        patch_ring="broad",
        installed_patch_level="2026-06",
        latest_available_patch="2026-06",
        disk_encryption="on",
        secure_boot=True,
        firewall_enabled=True,
        mdm_enrolled=True,
        edr_agent_healthy=True,
        last_checkin="2026-06-01T00:00:00Z",
        uptime_days=10,
        asset_owner="synthetic-user-001",
        notes="",
    )
    base.update(overrides)
    return Endpoint(**base)
