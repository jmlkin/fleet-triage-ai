"""Fleet Triage AI command-line interface (Typer + Rich).

    fleet-triage scan           # deterministic fleet-health report (table or json)
    fleet-triage report --ai    # report + AI exec summary (BYO key; sample fallback)
    fleet-triage runbook KEY    # Confluence-style remediation runbook
    fleet-triage generate-data  # regenerate the synthetic fleet
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from . import __version__
from .engine import analyze
from .loader import DEFAULT_DATA_PATH, load_fleet
from .render import render_terminal, to_json
from .ruleset import DEFAULT_RULESET_PATH, load_ruleset
from .runbooks import find_cluster, find_device, runbook_for_cluster, runbook_for_device

app = typer.Typer(add_completion=False, help="Policy-driven endpoint fleet-health triage with optional AI.")
console = Console()
err = Console(stderr=True)

_SAMPLES = Path(__file__).resolve().parents[2] / "samples"


def _load(data: Path, ruleset: Path):
    return analyze(load_fleet(data), load_ruleset(ruleset))


@app.command()
def scan(
    data: Path = typer.Option(DEFAULT_DATA_PATH, "--data", help="Path to fleet JSON."),
    ruleset: Path = typer.Option(DEFAULT_RULESET_PATH, "--ruleset", help="Path to policy YAML."),
    fmt: str = typer.Option("table", "--format", help="table | json"),
) -> None:
    """Run the deterministic engine and print the fleet-health report."""
    report = _load(data, ruleset)
    if fmt == "json":
        console.print_json(to_json(report))
    else:
        render_terminal(report, console)


@app.command()
def report(
    data: Path = typer.Option(DEFAULT_DATA_PATH, "--data"),
    ruleset: Path = typer.Option(DEFAULT_RULESET_PATH, "--ruleset"),
    ai: bool = typer.Option(False, "--ai", help="Append an AI executive summary (uses ANTHROPIC_API_KEY if set)."),
) -> None:
    """Full report plus an executive summary. Without a key, prints the committed sample."""
    rep = _load(data, ruleset)
    render_terminal(rep, console)
    if not ai:
        return

    console.rule("[bold]Executive summary")
    summary, mode = _executive_summary(rep)
    console.print(summary)
    console.print(f"\n[dim]({mode})[/dim]")


def _executive_summary(rep) -> tuple[str, str]:
    """Return (summary_markdown, mode). Falls back to the committed sample with no key."""
    try:
        from .ai import generate_executive_summary, has_key

        if has_key():
            return generate_executive_summary(rep), "live AI via ANTHROPIC_API_KEY"
    except Exception as exc:  # noqa: BLE001 - never let the demo crash on the AI path
        err.print(f"[yellow]AI path unavailable ({exc}); using committed sample.[/yellow]")

    sample = _SAMPLES / "executive_summary.md"
    if sample.exists():
        return sample.read_text(encoding="utf-8"), "sample, no API key used"
    return "(No sample available. Set ANTHROPIC_API_KEY and reinstall with `.[ai]` to generate live.)", "no key, no sample"


@app.command()
def runbook(
    key: str = typer.Argument(None, help="Cluster runbook key (see `scan`). Omit if using --device."),
    device: str = typer.Option(None, "--device", help="Device ID for a single-device runbook."),
    data: Path = typer.Option(DEFAULT_DATA_PATH, "--data"),
    ruleset: Path = typer.Option(DEFAULT_RULESET_PATH, "--ruleset"),
    out: Path = typer.Option(None, "--out", help="Write markdown to a file instead of stdout."),
) -> None:
    """Generate a Confluence-style remediation runbook for a cluster or device."""
    rep = _load(data, ruleset)

    if device:
        rb = find_device(rep, device)
        if not rb:
            err.print(f"[red]Device {device!r} not found in the at-risk set.[/red]")
            raise typer.Exit(1)
        md = runbook_for_device(rb)
    elif key:
        cl = find_cluster(rep, key)
        if not cl:
            keys = ", ".join(c.runbook_key for c in rep.clusters) or "(none)"
            err.print(f"[red]No cluster with key {key!r}.[/red] Available: {keys}")
            raise typer.Exit(1)
        md = runbook_for_cluster(cl, rep)
    else:
        err.print("[red]Provide a cluster KEY argument or --device ID.[/red]")
        raise typer.Exit(1)

    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
        console.print(f"[green]Wrote[/green] {out}")
    else:
        console.print(md)


@app.command(name="generate-data")
def generate_data(
    count: int = typer.Option(200, "--count"),
    seed: int = typer.Option(1337, "--seed"),
    out: Path = typer.Option(DEFAULT_DATA_PATH, "--out"),
) -> None:
    """Regenerate the synthetic fleet (deterministic for a given seed)."""
    from .generator import write

    written = write(out, count=count, seed=seed)
    console.print(f"[green]Wrote[/green] {written} synthetic endpoints to {out}")


@app.command()
def version() -> None:
    """Print the version."""
    console.print(f"fleet-triage-ai {__version__}")


if __name__ == "__main__":
    app()
