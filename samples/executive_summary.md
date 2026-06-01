<!-- Illustrative sample of the AI executive summary (committed so the value is
visible with no API key). With ANTHROPIC_API_KEY set, `fleet-triage report --ai`
generates this live from the current scan via the Anthropic API. Numbers match
the committed synthetic fleet (data/fleet.json). -->

# Fleet Health — Executive Summary

The fleet is **78% compliant** (156 of 200 endpoints), with 4 devices in the critical band and 36 at medium risk — a healthy majority, but with three clear, systemic problems rather than scattered noise.

**Patch drift on render-nodes (18 devices)** is the largest issue, concentrated in SEA (10 of 18). These are always-on render machines 4–5 months behind the approved patch build — consistent with a patch ring that never forces the reboot these never-idle hosts require. This is the highest-blast-radius cluster and should lead remediation.

**Disk encryption disabled on 9 edit-bays, all in ATX**, is a textbook bad-gold-image signature: every affected device shares one location and one role, pointing at a single imaging source rather than nine independent failures. Fixing the upstream image prevents recurrence on every future reimage.

**Stale MDM check-ins on 6 recording-booths** (offline 30–70 days) reflect intermittently-networked booths. Most are intentional, but they need a documented exception and a manual audit cadence so they stop masking real drift.

A scattered tail of 7 unmanaged / non-MDM-enrolled devices represents the highest per-device risk and should be enrolled or retired.

## Recommended actions
- Stage and force a reboot-window patch rollout to the 18 SEA render-nodes first.
- Re-image or enable encryption on the 9 ATX edit-bays, then fix the gold image.
- Enroll or decommission the 7 unmanaged devices this week.
- Document an exception + audit cadence for the offline booths.
- Add proactive alerts for patch drift > 2 months and check-in gaps > 14 days.
