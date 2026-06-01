# Fleet Triage AI

**A policy-driven endpoint fleet-health engine with a Model Context Protocol (MCP) interface and an optional bring-your-own-key AI layer. 100% synthetic data — safe to run, fork, and demo.**

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-21%20passing-brightgreen)
![No API key required](https://img.shields.io/badge/API%20key-not%20required-success)

Fleet Triage AI turns a raw fleet inventory of managed endpoints into **decisions**: a compliance score, a ranked list of at-risk machines, root-cause clusters, and ready-to-edit remediation runbooks — the way an endpoint-engineering or SRE lead actually triages a fleet. It's the open-source, synthetic-data twin of the kind of tooling I build for studio/production endpoint operations.

```text
+-------------------------------------------------- Fleet Triage AI ---------------------------------------------------+
| FLEET HEALTH   200 endpoints   as of 2026-06-01                                                                      |
| Compliant 156/200  (78.0%)     healthy 102  low 58  medium 36  critical 4                                            |
+----------------------------------------------------------------------------------------------------------------------+
                                                  Root-cause clusters
| Root cause                     |  Count | Correlates with                                 | Runbook                  |
| Patch drift                    |     18 | role=render-node (18/18), location=SEA (10/18)  | patch-drift-render-nodes |
| Disk encryption disabled       |      9 | role=edit-bay (9/9), location=ATX (9/9)         | encryption-off-edit-bays |
| Stale MDM check-in             |      6 | role=recording-booth (6/6), location=NYC (3/6)  | stale-checkin-booths     |
```

> Full sample output: [`samples/report.txt`](samples/report.txt) · structured JSON: [`samples/fleet_health.json`](samples/fleet_health.json)

---

## Why this exists

Most "AI portfolio" projects are a chatbot over a generic dataset. This one sits at the intersection of a **real operational domain** (endpoint/fleet management, compliance, patch strategy, remote-access hardening) and **modern AI tooling** (MCP servers, the Anthropic SDK, deterministic-core-plus-LLM-augmentation patterns). The hard part of fleet ops isn't calling an LLM — it's the explainable scoring, the root-cause correlation, and the runbook discipline. The AI sits *on top* of that, not in place of it.

## The three layers (and the no-API-key story)

This is the design decision that makes the repo usable by anyone, instantly:

| Layer | What it does | Needs a key? |
| --- | --- | --- |
| **1. Core engine** | Loads inventory → scores every device against a YAML policy → clusters at-risk devices by root cause → rich terminal report + JSON. | **No** — pure Python, no network. |
| **2. MCP server** | Exposes the engine as MCP tools so you can *talk to the fleet* from Claude Desktop / Claude Code. | **No** — your Claude client supplies the model; the server only returns data. |
| **3. Optional AI** | `--ai` flag generates an executive summary / enriches runbooks via the Anthropic API. | Only if you *want* it (`ANTHROPIC_API_KEY`). Falls back to committed samples otherwise. |

The core never imports `mcp` or `anthropic`; both higher layers call one public function, [`engine.analyze`](src/fleet_triage/engine.py) — so the CLI, the JSON, and the "talk to your fleet" answers can never disagree.

```
 fleet.json ──▶ ┌─────────────────────────┐ ──▶ rich report + JSON      (layer 1: no key)
 ruleset.yaml ─▶│  core engine (Python)   │
                │  score · cluster · rank │ ──▶ MCP tools ──▶ Claude client  (layer 2: no key)
                └─────────────────────────┘ ──▶ --ai summary (Anthropic SDK) (layer 3: opt-in key)
```

## Quickstart (zero key, zero cost)

```bash
git clone https://github.com/jmlkin/fleet-triage-ai.git
cd fleet-triage-ai
python -m venv .venv && . .venv/Scripts/activate   # macOS/Linux: source .venv/bin/activate
pip install -e .

fleet-triage scan                 # the rich fleet-health report
fleet-triage scan --format json   # structured FleetReport for piping
fleet-triage runbook encryption-off-edit-bays   # a Confluence-style remediation runbook
```

No API key. No network. No cost. The committed synthetic fleet (`data/fleet.json`) is the source of truth; regenerate it deterministically any time with `fleet-triage generate-data` (seed `1337`).

## Talk to your fleet (MCP)

Install the MCP extra and register the server with any MCP-capable Claude client:

```bash
pip install -e ".[mcp]"
```

Add this to your Claude Desktop config (`%APPDATA%/Claude/claude_desktop_config.json` on Windows, `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS) — full example in [`docs/claude_desktop_config.json`](docs/claude_desktop_config.json):

```json
{
  "mcpServers": {
    "fleet-triage": { "command": "fleet-triage-mcp" }
  }
}
```

Then ask Claude in plain language:

> **You:** What's the overall health of the fleet, and what's the biggest systemic problem?
>
> **Claude** *(calls `get_fleet_health`, then `get_clusters`)*: Fleet compliance is 78% (156/200). The largest systemic issue is **patch drift on render-nodes** — 18 devices 4–5 months behind, concentrated in SEA. Second is **disk encryption disabled on 9 edit-bays, all in ATX** — consistent with a bad gold image. Want a remediation runbook for either?
>
> **You:** Yes, the encryption one.
>
> **Claude** *(calls `generate_runbook`)*: *…returns a Confluence-style runbook with scope, root cause, steps, verification, and rollback.*

The server exposes six tools: `get_fleet_health`, `list_endpoints`, `get_compliance`, `get_clusters`, `suggest_remediation`, `generate_runbook`. **No API key is involved** — your Claude client does the reasoning; the server only returns ground-truth fleet data.

## Sample AI output (no key needed to see it)

- Executive summary: [`samples/executive_summary.md`](samples/executive_summary.md)
- Remediation runbooks: [`samples/runbooks/`](samples/runbooks/)

With a key set, `fleet-triage report --ai` generates the summary live; without one it prints the committed sample and says so.

## How the scoring works

Everything that defines "healthy" lives in [`config/ruleset.yaml`](config/ruleset.yaml) — not in code. A device is compliant only if it passes every hard-gate control (encryption on, MDM enrolled, EDR healthy, patch drift ≤ 2 months, checked in within 14 days). Risk is an explainable 0–100 weighted sum of failing controls × a role multiplier, and every contributing factor is retained so the report and runbooks can say *exactly why* a device scored what it did. Point the ruleset at your own baseline (CIS, internal hardening standard) and the engine re-scores the whole fleet.

## How it maps to real production-ops work

| In this repo (synthetic) | In a real studio/enterprise fleet |
| --- | --- |
| `data/fleet.json` | MDM / inventory export (Workspace ONE, Intune, Jamf) |
| `config/ruleset.yaml` | CIS / internal hardening baseline |
| Risk scoring + clustering | Root-cause analysis across a noisy fleet |
| Generated runbooks | Confluence remediation pages |
| MCP server | An operator-facing "talk to your fleet" copilot |

## Project layout

```
src/fleet_triage/   engine.py · scoring.py · clustering.py · runbooks.py · render.py · cli.py · mcp_server.py · ai.py
config/ruleset.yaml synthetic policy (thresholds + weights)
data/fleet.json     committed synthetic fleet (200 endpoints, seed 1337)
samples/            committed report, JSON, runbooks, AI summary
tests/              21 tests — golden scoring values, clustering, loader, MCP tools
```

## Testing

```bash
pip install -e ".[dev,mcp]"
pytest -q
```

Golden-value tests pin the end-to-end behavior to the seeded fleet, so any regression in scoring, clustering, or the generator is caught immediately.

## License

MIT — see [LICENSE](LICENSE). All data is synthetic; no real systems, people, or organizations are represented.
