"""Terminal (Rich) and JSON renderers for a FleetReport.

The JSON view is the same structure the MCP tools return, so screenshots,
`--format json`, and the "talk to your fleet" answers all line up.
"""

from __future__ import annotations

import json

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .models import FleetReport

_BAND_STYLE = {"healthy": "green", "low": "yellow", "medium": "dark_orange", "critical": "bold red"}


def to_json(report: FleetReport, indent: int = 2) -> str:
    return json.dumps(report.to_dict(), indent=indent)


def render_terminal(report: FleetReport, console: Console | None = None) -> None:
    console = console or Console()
    sc = report.severity_counts

    header = (
        f"[bold]FLEET HEALTH[/bold]   {report.total} endpoints   "
        f"as of {report.generated_at[:10]}\n"
        f"Compliant [bold green]{report.compliant}[/bold green]/"
        f"{report.total}  ([bold]{report.compliance_pct}%[/bold])     "
        f"healthy [green]{sc['healthy']}[/green]  "
        f"low [yellow]{sc['low']}[/yellow]  "
        f"medium [dark_orange]{sc['medium']}[/dark_orange]  "
        f"critical [bold red]{sc['critical']}[/bold red]"
    )
    console.print(Panel(header, title="Fleet Triage AI", border_style="cyan"))

    # Root-cause clusters — the headline finding.
    if report.clusters:
        ct = Table(title="Root-cause clusters", title_style="bold", header_style="bold cyan", expand=True)
        ct.add_column("Root cause")
        ct.add_column("Count", justify="right")
        ct.add_column("Correlates with")
        ct.add_column("Runbook")
        for c in report.clusters:
            ct.add_row(c.title, str(c.affected_count), c.correlate, c.runbook_key)
        console.print(ct)

    # Top at-risk devices.
    rt = Table(title=f"At-risk devices ({len(report.at_risk)})", title_style="bold",
               header_style="bold cyan", expand=True)
    rt.add_column("Risk", justify="right")
    rt.add_column("Device")
    rt.add_column("Role")
    rt.add_column("Loc")
    rt.add_column("Top issue")
    for b in report.at_risk[:15]:
        dom = b.dominant
        rt.add_row(
            f"[{_BAND_STYLE[b.band]}]{b.risk}[/{_BAND_STYLE[b.band]}]",
            b.hostname,
            b.role,
            b.location,
            dom.detail if dom else "-",
        )
    console.print(rt)
    if len(report.at_risk) > 15:
        console.print(f"[dim]...and {len(report.at_risk) - 15} more. Use --format json for the full list.[/dim]")

    # Compliance by role.
    brt = Table(title="Compliance by role", title_style="bold", header_style="bold cyan")
    brt.add_column("Role")
    brt.add_column("Compliant", justify="right")
    brt.add_column("%", justify="right")
    for role, stats in report.by_role.items():
        brt.add_row(role, f"{stats['compliant']}/{stats['total']}", f"{stats['compliance_pct']}%")
    console.print(brt)
