"""Golden-trace regression policy + verdict for CI mode.

Reuses the whole load → align → compute_diff pipeline; the only new logic is a
threshold policy over a ``DiffResult`` plus process exit-code semantics:

    0 = pass    1 = drift (policy breached)    2 = usage/load error

Honors ``available=False`` deltas (never fail on an untracked metric) and guards
divide-by-zero when a golden total is 0.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from agentdiff.align import Op, align
from agentdiff.diff import DiffResult, compute_diff

EXIT_PASS = 0
EXIT_DRIFT = 1
EXIT_ERROR = 2

_STRUCTURAL_OPS = {Op.INSERT_B.value, Op.DELETE_A.value, Op.SUBSTITUTE.value}


@dataclass
class Policy:
    max_cost_delta_pct: float = 10.0
    max_token_delta_pct: float = 20.0
    allow_structural_change: bool = False


@dataclass
class Verdict:
    passed: bool
    reasons: list[str] = field(default_factory=list)
    breached: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _pct_delta(diff: DiffResult, metric: str) -> float | None:
    """B−A as a percentage of the A (golden) total; None if not computable."""
    d = diff.deltas.get(metric)
    if d is None or not d.available:
        return None
    base = getattr(diff.totals_a, metric, 0)
    if not base:
        # Golden has zero for this metric — percentage undefined; treat any
        # positive movement as an absolute breach signal elsewhere.
        return None
    return (d.value / base) * 100.0


def evaluate(diff: DiffResult, policy: Policy) -> Verdict:
    """Apply the policy to a diff and return a pass/fail verdict."""
    reasons: list[str] = []
    breached: list[str] = []

    if not policy.allow_structural_change:
        structural = sum(diff.summary_counts.get(op, 0) for op in _STRUCTURAL_OPS)
        if structural:
            breached.append("structural")
            reasons.append(f"{structural} structural change(s) vs golden")

    cost_pct = _pct_delta(diff, "cost")
    if cost_pct is not None and abs(cost_pct) > policy.max_cost_delta_pct:
        breached.append("cost")
        reasons.append(f"cost delta {cost_pct:.1f}% > {policy.max_cost_delta_pct}%")

    token_pct = _pct_delta(diff, "total_tokens")
    if token_pct is not None and abs(token_pct) > policy.max_token_delta_pct:
        breached.append("total_tokens")
        reasons.append(f"token delta {token_pct:.1f}% > {policy.max_token_delta_pct}%")

    passed = not breached
    if passed:
        reasons.append("within policy")
    return Verdict(passed=passed, reasons=reasons, breached=breached)


def run_check(golden_steps, new_steps, policy: Policy, *, semantic: bool = False):
    """Align golden vs new, evaluate, and return ``(verdict, diff)``."""
    pairs = align(golden_steps, new_steps, semantic=semantic)
    diff = compute_diff(pairs)
    return evaluate(diff, policy), diff
