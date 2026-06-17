"""Diff + delta computation over aligned pairs.

Produces a ``DiffResult`` — the single serializable source of truth consumed by
both the HTML viewer (P4) and the CI mode (P6). No re-derivation downstream.

Delta convention: **B minus A**. B is the new/candidate run, A is the
baseline/golden. Every label downstream follows this sign.
"""

from __future__ import annotations

import difflib
from dataclasses import asdict, dataclass, field

from agentdiff.align import AlignedPair, Op

_METRICS = ("tokens_in", "tokens_out", "total_tokens", "cost", "latency_ms", "tool_calls")


@dataclass
class Totals:
    tokens_in: float = 0.0
    tokens_out: float = 0.0
    total_tokens: float = 0.0
    cost: float = 0.0
    latency_ms: float = 0.0
    tool_calls: int = 0


@dataclass
class Delta:
    value: float = 0.0
    available: bool = True


@dataclass
class DiffResult:
    pairs: list[dict] = field(default_factory=list)
    first_divergence_index: int | None = None
    totals_a: Totals = field(default_factory=Totals)
    totals_b: Totals = field(default_factory=Totals)
    deltas: dict[str, Delta] = field(default_factory=dict)
    summary_counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Stable JSON-safe shape for the viewer template + CI parsers."""
        return {
            "pairs": self.pairs,
            "first_divergence_index": self.first_divergence_index,
            "totals_a": asdict(self.totals_a),
            "totals_b": asdict(self.totals_b),
            "deltas": {k: asdict(v) for k, v in self.deltas.items()},
            "summary_counts": self.summary_counts,
        }


def _sum_totals(pairs: list[AlignedPair], side: str) -> Totals:
    totals = Totals()
    for pair in pairs:
        step = getattr(pair, side)
        if step is None:
            continue
        totals.tokens_in += step.tokens_in
        totals.tokens_out += step.tokens_out
        totals.total_tokens += step.total_tokens
        totals.cost += step.cost
        totals.latency_ms += step.latency_ms
        totals.tool_calls += 1 if step.is_tool_call else 0
    return totals


def inline_text_diff(a: str, b: str) -> list[dict]:
    """difflib opcodes describing how to turn ``a`` into ``b`` (for SUBSTITUTE)."""
    sm = difflib.SequenceMatcher(a=a, b=b)
    return [
        {"tag": tag, "a": a[i1:i2], "b": b[j1:j2]}
        for tag, i1, i2, j1, j2 in sm.get_opcodes()
    ]


def _pair_to_dict(pair: AlignedPair) -> dict:
    out: dict = {"op": pair.op.value, "score": round(pair.score, 4)}
    out["a"] = _step_view(pair.a)
    out["b"] = _step_view(pair.b)
    if pair.op is Op.SUBSTITUTE and pair.a and pair.b:
        out["inline"] = inline_text_diff(pair.a.content, pair.b.content)
    return out


def _step_view(step) -> dict | None:
    if step is None:
        return None
    return {
        "step": step.step,
        "role": step.role,
        "label": step.label(),
        "content": step.content,
        "tool_name": step.tool_name,
        "tool_args": step.tool_args,
        "tokens_in": step.tokens_in,
        "tokens_out": step.tokens_out,
        "total_tokens": step.total_tokens,
        "cost": step.cost,
        "latency_ms": step.latency_ms,
    }


def compute_diff(pairs: list[AlignedPair]) -> DiffResult:
    """Classify pairs, find first divergence, and compute B−A deltas."""
    totals_a = _sum_totals(pairs, "a")
    totals_b = _sum_totals(pairs, "b")

    deltas: dict[str, Delta] = {}
    for metric in _METRICS:
        va = getattr(totals_a, metric)
        vb = getattr(totals_b, metric)
        available = not (va == 0 and vb == 0)
        deltas[metric] = Delta(value=vb - va, available=available)

    first_divergence = next(
        (idx for idx, p in enumerate(pairs) if p.op is not Op.MATCH), None
    )

    counts = {op.value: 0 for op in Op}
    for pair in pairs:
        counts[pair.op.value] += 1

    return DiffResult(
        pairs=[_pair_to_dict(p) for p in pairs],
        first_divergence_index=first_divergence,
        totals_a=totals_a,
        totals_b=totals_b,
        deltas=deltas,
        summary_counts=counts,
    )
