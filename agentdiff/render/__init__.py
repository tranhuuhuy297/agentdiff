"""Rendering: DiffResult → self-contained HTML, or a colored terminal diff.

``render_html`` is pure (returns a string). File writing and browser opening live
in the CLI. The HTML embeds the diff as a JSON blob and builds the DOM with
``textContent`` so no external requests are made and trace content can't inject
script.
"""

from __future__ import annotations

import json
from importlib.resources import files

from jinja2 import Environment, select_autoescape
from rich.console import Console
from rich.table import Table
from rich.text import Text

from agentdiff.diff import DiffResult

_OP_STYLE = {
    "match": "dim",
    "substitute": "yellow",
    "insert_b": "green",
    "delete_a": "red",
}


def _load_template() -> str:
    """Read the packaged Jinja template (works installed, not just from source)."""
    return files("agentdiff.render").joinpath("viewer.html.j2").read_text(encoding="utf-8")


def render_html(diff: DiffResult, meta: dict | None = None) -> str:
    """Render a ``DiffResult`` to a single self-contained HTML document."""
    meta = meta or {}
    env = Environment(autoescape=select_autoescape(["html"]))
    template = env.from_string(_load_template())
    # json.dumps escapes "</script>" sequences via default ensure_ascii handling;
    # additionally guard the closing tag to keep the embedded blob inert.
    diff_json = json.dumps(diff.to_dict()).replace("</", "<\\/")
    return template.render(
        title=meta.get("title", "trace diff"),
        source_a=meta.get("source_a", "A"),
        source_b=meta.get("source_b", "B"),
        diff_json=diff_json,
    )


def render_terminal(diff: DiffResult, console: Console | None = None) -> None:
    """Print a colored side-by-side diff + delta summary to the terminal."""
    console = console or Console()

    # Delta summary line (skip unavailable metrics).
    parts = []
    for key, label in (
        ("total_tokens", "tokens"),
        ("cost", "cost"),
        ("latency_ms", "latency_ms"),
        ("tool_calls", "tools"),
    ):
        d = diff.deltas.get(key)
        if d and d.available:
            sign = "+" if d.value > 0 else ""
            parts.append(f"Δ{label} {sign}{round(d.value, 3)}")
    console.print("  ".join(parts) or "no metric deltas", style="bold")

    div = diff.first_divergence_index
    console.print(
        "✓ no divergence" if div is None else f"first divergence at row {div + 1}",
        style="magenta",
    )

    table = Table(show_lines=False, expand=True)
    table.add_column("#", justify="right", style="dim", no_wrap=True)
    table.add_column("A (baseline)")
    table.add_column("B (candidate)")
    for idx, pair in enumerate(diff.pairs):
        style = _OP_STYLE.get(pair["op"], "")
        a = pair["a"]["content"] if pair["a"] else ""
        b = pair["b"]["content"] if pair["b"] else ""
        table.add_row(str(idx + 1), Text(a, style=style), Text(b, style=style))
    console.print(table)
