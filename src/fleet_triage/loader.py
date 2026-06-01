"""Reads and validates a synthetic fleet file into typed `FleetData`.

Accepts either the canonical wrapped form `{"as_of": ..., "endpoints": [...]}`
or a bare list of endpoint records (in which case `as_of` defaults to now).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import LOCATIONS, OSES, ROLES, Endpoint, FleetData

DEFAULT_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "fleet.json"

_REQUIRED = {
    "device_id", "hostname", "role", "location", "os", "os_version",
    "patch_ring", "installed_patch_level", "latest_available_patch",
    "disk_encryption", "secure_boot", "firewall_enabled", "mdm_enrolled",
    "edr_agent_healthy", "last_checkin", "uptime_days", "asset_owner",
}


def _validate(rec: dict, idx: int) -> None:
    missing = _REQUIRED - rec.keys()
    if missing:
        raise ValueError(f"endpoint #{idx} ({rec.get('device_id', '?')}) missing fields: {sorted(missing)}")
    if rec["role"] not in ROLES:
        raise ValueError(f"endpoint #{idx}: unknown role {rec['role']!r}")
    if rec["location"] not in LOCATIONS:
        raise ValueError(f"endpoint #{idx}: unknown location {rec['location']!r}")
    if rec["os"] not in OSES:
        raise ValueError(f"endpoint #{idx}: unknown os {rec['os']!r}")


def load_fleet(path: str | Path | None = None) -> FleetData:
    p = Path(path) if path else DEFAULT_DATA_PATH
    raw = json.loads(p.read_text(encoding="utf-8"))

    if isinstance(raw, dict):
        as_of = raw.get("as_of") or datetime.now(timezone.utc).isoformat()
        records = raw["endpoints"]
    else:
        as_of = datetime.now(timezone.utc).isoformat()
        records = raw

    endpoints: list[Endpoint] = []
    for idx, rec in enumerate(records):
        _validate(rec, idx)
        endpoints.append(Endpoint(**{k: rec[k] for k in rec if k in Endpoint.__dataclass_fields__}))

    return FleetData(as_of=as_of, endpoints=endpoints)
