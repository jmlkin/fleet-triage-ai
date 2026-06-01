"""Typed data model for the fleet engine.

Plain dataclasses (no third-party deps) so the core stays trivially importable
and testable. `to_dict` gives a JSON-serializable view of the whole report.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

ROLES = ("recording-booth", "edit-bay", "render-node", "laptop", "conference-room")
LOCATIONS = ("SEA", "NYC", "LON", "ATX", "REMOTE")
OSES = ("macOS", "Windows", "Ubuntu")


@dataclass
class Endpoint:
    """One managed device as it would appear in an MDM / inventory export.

    Every identifier is synthetic by construction (FLT-* ids, synthetic-user-*
    owners, generic location codes) so the dataset is safe to open-source.
    """

    device_id: str
    hostname: str
    role: str
    location: str
    os: str
    os_version: str
    patch_ring: str            # canary | early | broad | unmanaged
    installed_patch_level: str  # YYYY-MM
    latest_available_patch: str  # YYYY-MM
    disk_encryption: str        # on | off | unknown
    secure_boot: bool
    firewall_enabled: bool
    mdm_enrolled: bool
    edr_agent_healthy: bool
    last_checkin: str           # ISO-8601 UTC
    uptime_days: int
    asset_owner: str
    notes: str = ""


@dataclass
class RiskFactor:
    """A single control that failed, with its point contribution and a reason."""

    control: str
    points: int
    detail: str


@dataclass
class RiskBreakdown:
    """Per-device verdict: the score, the band, compliance, and *why*."""

    device_id: str
    hostname: str
    role: str
    location: str
    risk: int
    band: str                   # healthy | low | medium | critical
    compliant: bool
    factors: list[RiskFactor] = field(default_factory=list)

    @property
    def dominant(self) -> RiskFactor | None:
        """The single highest-weighted failing control (drives clustering)."""
        return max(self.factors, key=lambda f: f.points) if self.factors else None


@dataclass
class Cluster:
    """A root-cause grouping of at-risk devices that share a dominant fault."""

    root_cause: str             # control key, e.g. "patch_drift"
    title: str                  # human label
    affected_count: int
    correlate: str              # e.g. "role=edit-bay (9/9), location=ATX (9/9)"
    example_device_ids: list[str]
    runbook_key: str


@dataclass
class FleetReport:
    """The full deterministic analysis of a fleet at a point in time."""

    generated_at: str
    total: int
    compliant: int
    compliance_pct: float
    severity_counts: dict       # band -> count
    by_role: dict               # role -> {total, compliant, compliance_pct}
    by_location: dict           # location -> {total, compliant, compliance_pct}
    at_risk: list[RiskBreakdown]
    clusters: list[Cluster]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FleetData:
    """A loaded fleet file: the endpoints plus the reference 'as of' time used
    for staleness math. Wrapping the array keeps scans reproducible regardless
    of the real wall-clock date."""

    as_of: str
    endpoints: list[Endpoint]
