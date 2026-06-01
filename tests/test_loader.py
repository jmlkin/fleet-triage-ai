import json

import pytest

from fleet_triage.loader import load_fleet


def _write(tmp_path, payload):
    p = tmp_path / "fleet.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


def _valid_record():
    return {
        "device_id": "FLT-0001", "hostname": "laptop-remote-001", "role": "laptop",
        "location": "REMOTE", "os": "Windows", "os_version": "11.0.26100",
        "patch_ring": "broad", "installed_patch_level": "2026-06",
        "latest_available_patch": "2026-06", "disk_encryption": "on",
        "secure_boot": True, "firewall_enabled": True, "mdm_enrolled": True,
        "edr_agent_healthy": True, "last_checkin": "2026-06-01T00:00:00Z",
        "uptime_days": 3, "asset_owner": "synthetic-user-001",
    }


def test_loads_wrapped_form(tmp_path):
    p = _write(tmp_path, {"as_of": "2026-06-01T00:00:00Z", "endpoints": [_valid_record()]})
    data = load_fleet(p)
    assert data.as_of.startswith("2026-06-01")
    assert len(data.endpoints) == 1


def test_rejects_missing_field(tmp_path):
    rec = _valid_record()
    del rec["disk_encryption"]
    p = _write(tmp_path, {"endpoints": [rec]})
    with pytest.raises(ValueError, match="missing fields"):
        load_fleet(p)


def test_rejects_unknown_role(tmp_path):
    rec = _valid_record()
    rec["role"] = "toaster"
    p = _write(tmp_path, {"endpoints": [rec]})
    with pytest.raises(ValueError, match="unknown role"):
        load_fleet(p)
