"""Per-endpoint scoring: compliance (hard gate) + explainable risk score.

Pure functions, no side effects. Every failing control is recorded as a
`RiskFactor` so the report and runbooks can explain exactly why a device
scored what it did.
"""

from __future__ import annotations

from datetime import datetime

from .models import Endpoint, RiskBreakdown, RiskFactor
from .ruleset import Ruleset


def months_behind(installed: str, latest: str) -> int:
    """Whole months between two YYYY-MM patch levels (never negative)."""
    iy, im = (int(x) for x in installed.split("-"))
    ly, lm = (int(x) for x in latest.split("-"))
    return max(0, (ly - iy) * 12 + (lm - im))


def _parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def days_since_checkin(last_checkin: str, as_of: datetime) -> int:
    delta = as_of - _parse_iso(last_checkin)
    return max(0, delta.days)


def is_compliant(ep: Endpoint, rs: Ruleset, drift: int, stale_days: int) -> bool:
    c = rs.compliance
    if c.get("require_disk_encryption", True) and ep.disk_encryption != "on":
        return False
    if c.get("require_mdm_enrolled", True) and not ep.mdm_enrolled:
        return False
    if c.get("require_edr_healthy", True) and not ep.edr_agent_healthy:
        return False
    if drift > int(c["max_patch_drift_months"]):
        return False
    if stale_days > int(c["stale_checkin_days"]):
        return False
    return True


def _band(risk: int, rs: Ruleset) -> str:
    if risk <= 0:
        return "healthy"
    if risk >= int(rs.bands["critical_min"]):
        return "critical"
    if risk >= int(rs.bands["medium_min"]):
        return "medium"
    return "low"


def evaluate(ep: Endpoint, rs: Ruleset, as_of: datetime) -> RiskBreakdown:
    rw = rs.risk_weights
    factors: list[RiskFactor] = []

    if ep.disk_encryption != "on":
        factors.append(RiskFactor("encryption_off", int(rw["encryption_off"]),
                                  f"disk encryption is {ep.disk_encryption}"))
    if not ep.mdm_enrolled:
        factors.append(RiskFactor("mdm_unenrolled", int(rw["mdm_unenrolled"]),
                                  "not enrolled in MDM"))

    drift = months_behind(ep.installed_patch_level, ep.latest_available_patch)
    if drift > 0:
        pts = min(drift * int(rw["patch_drift_per_month"]), int(rw["patch_drift_cap"]))
        factors.append(RiskFactor("patch_drift", pts,
                                  f"{drift} month(s) behind ({ep.installed_patch_level} -> {ep.latest_available_patch})"))

    if not ep.edr_agent_healthy:
        factors.append(RiskFactor("edr_unhealthy", int(rw["edr_unhealthy"]),
                                  "EDR agent not reporting healthy"))
    if not ep.firewall_enabled:
        factors.append(RiskFactor("firewall_off", int(rw["firewall_off"]),
                                  "host firewall disabled"))
    if not ep.secure_boot:
        factors.append(RiskFactor("secure_boot_off", int(rw["secure_boot_off"]),
                                  "secure boot disabled"))
    if ep.patch_ring == "unmanaged":
        factors.append(RiskFactor("unmanaged_ring", int(rw["unmanaged_ring"]),
                                  "device is on the unmanaged patch ring"))

    stale_days = days_since_checkin(ep.last_checkin, as_of)
    for tier in rw["stale_checkin_tiers"]:  # ordered high -> low; first match wins
        if stale_days >= int(tier["days"]):
            factors.append(RiskFactor("stale_checkin", int(tier["points"]),
                                      f"{stale_days} days since last check-in"))
            break

    raw = sum(f.points for f in factors)
    multiplier = float(rs.role_multipliers.get(ep.role, 1.0))
    risk = min(100, round(raw * multiplier))

    return RiskBreakdown(
        device_id=ep.device_id,
        hostname=ep.hostname,
        role=ep.role,
        location=ep.location,
        risk=risk,
        band=_band(risk, rs),
        compliant=is_compliant(ep, rs, drift, stale_days),
        factors=factors,
    )
