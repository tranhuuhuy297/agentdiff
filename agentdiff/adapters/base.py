"""Adapter contract + shared field normalization.

Every adapter maps a foreign export into the canonical ``Step``/``Trace`` model
via the helpers here (DRY — JSONL, OTel and Langfuse all reuse ``normalize_step``).
"""

from __future__ import annotations

from typing import Any, Protocol

from agentdiff.models import Step, Trace

# Generous guard against pathological inputs (256 MiB). Adapters reading whole
# files should honor this before parsing.
MAX_BYTES = 256 * 1024 * 1024


class Adapter(Protocol):
    """Structural contract: a callable ``load(path) -> Trace``."""

    def __call__(self, path: str) -> Trace: ...


def coerce_number(value: Any, default: float | int = 0) -> float | int:
    """Best-effort numeric coercion: None/""/garbage -> default."""
    if value is None or value == "":
        return default
    try:
        num = float(value)
    except (TypeError, ValueError):
        return default
    return int(num) if num.is_integer() else num


def _coerce_int(value: Any) -> int:
    return int(coerce_number(value, 0))


def normalize_step(raw: dict, *, index: int | None = None) -> Step:
    """Map a raw dict onto a ``Step``, applying defaults.

    ``index`` provides the fallback ``step`` value when the source omits it
    (e.g. JSONL line order, OTel timestamp order).
    """
    step_idx = raw.get("step")
    step_idx = int(step_idx) if step_idx is not None else (index if index is not None else 0)

    tool_args = raw.get("tool_args")
    if tool_args is not None and not isinstance(tool_args, dict):
        tool_args = {"value": tool_args}

    known = {
        "step", "role", "content", "tool_name", "tool_args",
        "tokens_in", "tokens_out", "cost", "latency_ms",
    }
    extra = {k: v for k, v in raw.items() if k not in known}

    return Step(
        step=step_idx,
        role=str(raw.get("role") or ""),
        content=str(raw.get("content") or ""),
        tool_name=(raw.get("tool_name") or None),
        tool_args=tool_args,
        tokens_in=_coerce_int(raw.get("tokens_in")),
        tokens_out=_coerce_int(raw.get("tokens_out")),
        cost=float(coerce_number(raw.get("cost"), 0.0)),
        latency_ms=float(coerce_number(raw.get("latency_ms"), 0.0)),
        extra=extra,
    )


def finalize(steps: list[Step], meta: dict) -> Trace:
    """Sort by step index (stable) and wrap in a ``Trace``.

    Out-of-order/duplicate indices are tolerated — sorting fixes order and a
    note is recorded in ``meta`` rather than crashing.
    """
    indices = [s.step for s in steps]
    if indices != sorted(indices):
        meta = {**meta, "reordered": True}
    steps_sorted = sorted(steps, key=lambda s: s.step)
    return Trace(steps=steps_sorted, meta=meta)
