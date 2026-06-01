"""Rule-based root-cause clustering of at-risk devices (no ML).

Groups at-risk devices by their dominant failing control, then finds the
strongest role/location correlate inside each group. This deterministically
surfaces story-shaped findings like "9 edit-bays, all in ATX, encryption off".
"""

from __future__ import annotations

from collections import Counter, defaultdict

from .models import Cluster, RiskBreakdown

CONTROL_TITLES = {
    "patch_drift": "Patch drift",
    "encryption_off": "Disk encryption disabled",
    "stale_checkin": "Stale MDM check-in",
    "mdm_unenrolled": "Unmanaged / not MDM-enrolled",
    "unmanaged_ring": "Unmanaged patch ring",
    "edr_unhealthy": "EDR agent unhealthy",
    "firewall_off": "Host firewall disabled",
    "secure_boot_off": "Secure boot disabled",
}

# Pluralization for runbook slugs; recording-booth collapses to "booths".
_ROLE_PLURAL = {
    "render-node": "render-nodes",
    "edit-bay": "edit-bays",
    "recording-booth": "booths",
    "laptop": "laptops",
    "conference-room": "conference-rooms",
}


def _strongest_correlate(members: list[RiskBreakdown]) -> str:
    n = len(members)
    role_val, role_n = Counter(m.role for m in members).most_common(1)[0]
    loc_val, loc_n = Counter(m.location for m in members).most_common(1)[0]
    role_frac, loc_frac = role_n / n, loc_n / n

    ordered = sorted(
        [("role", role_val, role_n, role_frac), ("location", loc_val, loc_n, loc_frac)],
        key=lambda t: t[3],
        reverse=True,
    )
    parts = [f"{ordered[0][0]}={ordered[0][1]} ({ordered[0][2]}/{n})"]
    # Include the secondary dimension only when it is itself concentrated.
    if ordered[1][3] >= 0.5:
        parts.append(f"{ordered[1][0]}={ordered[1][1]} ({ordered[1][2]}/{n})")
    return ", ".join(parts)


def _runbook_key(control: str, members: list[RiskBreakdown]) -> str:
    top_role = Counter(m.role for m in members).most_common(1)[0][0]
    control_slug = control.replace("_", "-")
    return f"{control_slug}-{_ROLE_PLURAL.get(top_role, top_role)}"


def build_clusters(at_risk: list[RiskBreakdown], min_count: int = 2) -> list[Cluster]:
    buckets: dict[str, list[RiskBreakdown]] = defaultdict(list)
    for rb in at_risk:
        dom = rb.dominant
        if dom is not None:
            buckets[dom.control].append(rb)

    clusters: list[Cluster] = []
    for control, members in buckets.items():
        if len(members) < min_count:
            continue
        members_sorted = sorted(members, key=lambda m: m.risk, reverse=True)
        clusters.append(Cluster(
            root_cause=control,
            title=CONTROL_TITLES.get(control, control),
            affected_count=len(members_sorted),
            correlate=_strongest_correlate(members_sorted),
            example_device_ids=[m.device_id for m in members_sorted[:4]],
            runbook_key=_runbook_key(control, members_sorted),
        ))

    clusters.sort(key=lambda c: c.affected_count, reverse=True)
    return clusters
