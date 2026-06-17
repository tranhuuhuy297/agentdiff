"""agentdiff CLI — load → align → diff → render / gate.

Commands:
  diff A B      Visual diff of two runs (HTML report or --terminal).
  check NEW     Gate a run against a --golden reference; exits 0/1/2 for CI.
  golden NEW    Save a run as a golden reference file.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import webbrowser

import typer
from rich.console import Console

from agentdiff import __version__
from agentdiff.adapters import load_trace
from agentdiff.align import DEFAULT_GAP_PENALTY, DEFAULT_MATCH_THRESHOLD, align
from agentdiff.ci import EXIT_DRIFT, EXIT_ERROR, EXIT_PASS, Policy, evaluate, run_check
from agentdiff.config import load_config, merge_flags
from agentdiff.diff import compute_diff
from agentdiff.models import TraceParseError
from agentdiff.render import render_html, render_terminal

app = typer.Typer(add_completion=False, help="git diff, but for AI agent runs.")
_err = Console(stderr=True)

_FMT_HELP = "Force input format: jsonl | otel | langfuse (default: auto-detect)."


def _version_cb(value: bool) -> None:
    if value:
        typer.echo(f"agentdiff {__version__}")
        raise typer.Exit()


@app.callback()
def _main(
    _version: bool = typer.Option(
        False, "--version", callback=_version_cb, is_eager=True, help="Show version and exit."
    ),
) -> None:
    """agentdiff — align two agent run trajectories and report the delta."""


def _load(path: str, fmt: str | None):
    try:
        return load_trace(path, fmt)
    except TraceParseError as exc:
        _err.print(f"[red]error[/red] loading {path}: {exc}")
        raise typer.Exit(EXIT_ERROR) from exc


def _headless() -> bool:
    """Don't try to open a browser in CI / headless environments."""
    if os.environ.get("CI"):
        return True
    return sys.platform.startswith("linux") and not os.environ.get("DISPLAY")


@app.command()
def diff(
    a: str = typer.Argument(..., help="Baseline trace (A)."),
    b: str = typer.Argument(..., help="Candidate trace (B)."),
    out: str = typer.Option("agentdiff-report.html", "--out", "-o", help="HTML output path."),
    no_open: bool = typer.Option(False, "--no-open", help="Do not open a browser."),
    terminal: bool = typer.Option(False, "--terminal", "-t", help="Print a colored terminal diff."),
    semantic: bool = typer.Option(False, "--semantic", help="Embedding similarity (opt-in)."),
    fmt: str | None = typer.Option(None, "--format", "-f", help=_FMT_HELP),
    gap: float = typer.Option(DEFAULT_GAP_PENALTY, "--gap", help="Alignment gap penalty."),
    threshold: float = typer.Option(DEFAULT_MATCH_THRESHOLD, "--threshold", help="Match cutoff."),
) -> None:
    """Diff two agent runs → HTML report (or terminal)."""
    trace_a = _load(a, fmt)
    trace_b = _load(b, fmt)
    pairs = align(
        trace_a.steps, trace_b.steps,
        semantic=semantic, gap_penalty=gap, match_threshold=threshold,
    )
    result = compute_diff(pairs)

    if terminal:
        render_terminal(result)
        return

    title = f"{os.path.basename(a)} ↔ {os.path.basename(b)}"
    html = render_html(result, meta={"title": title, "source_a": a, "source_b": b})
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)
    _err.print(f"[green]wrote[/green] {out}")
    if not no_open and not _headless():
        webbrowser.open(f"file://{os.path.abspath(out)}")


@app.command()
def check(
    new: str = typer.Argument(..., help="New/candidate run to gate."),
    golden: str = typer.Option(..., "--golden", "-g", help="Golden reference run."),
    config: str | None = typer.Option(None, "--config", help="Path to agentdiff.toml."),
    max_cost_delta_pct: float | None = typer.Option(None, "--max-cost-delta-pct"),
    max_token_delta_pct: float | None = typer.Option(None, "--max-token-delta-pct"),
    allow_structural_change: bool | None = typer.Option(None, "--allow-structural-change"),
    semantic: bool = typer.Option(False, "--semantic"),
    fmt: str | None = typer.Option(None, "--format", "-f", help=_FMT_HELP),
    json_out: str | None = typer.Option(None, "--json", help="Write verdict JSON."),
    report_html: str | None = typer.Option(None, "--report-html", help="Write HTML on failure."),
) -> None:
    """Gate a run against a golden reference. Exit 0 pass / 1 drift / 2 error."""
    cfg = merge_flags(
        load_config(config),
        max_cost_delta_pct=max_cost_delta_pct,
        max_token_delta_pct=max_token_delta_pct,
        allow_structural_change=allow_structural_change,
    )
    policy = Policy(
        max_cost_delta_pct=cfg["max_cost_delta_pct"],
        max_token_delta_pct=cfg["max_token_delta_pct"],
        allow_structural_change=cfg["allow_structural_change"],
    )

    golden_trace = _load(golden, fmt)
    new_trace = _load(new, fmt)
    verdict, result = run_check(golden_trace.steps, new_trace.steps, policy, semantic=semantic)

    if json_out:
        with open(json_out, "w", encoding="utf-8") as fh:
            json.dump({"verdict": verdict.to_dict(), "diff": result.to_dict()}, fh, indent=2)
    if report_html and not verdict.passed:
        meta = {"title": "golden-trace check", "source_a": golden, "source_b": new}
        with open(report_html, "w", encoding="utf-8") as fh:
            fh.write(render_html(result, meta=meta))

    status = "PASS" if verdict.passed else "DRIFT"
    color = "green" if verdict.passed else "red"
    _err.print(f"[{color}]{status}[/{color}] — {'; '.join(verdict.reasons)}")
    raise typer.Exit(EXIT_PASS if verdict.passed else EXIT_DRIFT)


@app.command()
def golden(
    new: str = typer.Argument(..., help="Run to save as the golden reference."),
    out: str = typer.Option(..., "--out", "-o", help="Destination golden file path."),
) -> None:
    """Save a run as a golden reference (a verbatim copy)."""
    if not os.path.exists(new):
        _err.print(f"[red]error[/red] file not found: {new}")
        raise typer.Exit(EXIT_ERROR)
    shutil.copyfile(new, out)
    _err.print(f"[green]saved golden[/green] {out}")


# Keep `evaluate` importable here for tests that exercise the CLI surface.
__all__ = ["app", "evaluate"]
