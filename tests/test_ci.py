"""CI mode: evaluate policy, exit-code semantics, json verdict shape."""

from __future__ import annotations

from agentdiff.ci import EXIT_DRIFT, EXIT_ERROR, EXIT_PASS, Policy, evaluate, run_check
from agentdiff.models import Step


def _s(i, content="x", **kw):
    return Step(step=i, role="assistant", content=content, **kw)


def test_identical_passes():
    a = [_s(0, "hello there friend"), _s(1, "second line here", tokens_in=10, cost=0.001)]
    verdict, _ = run_check(a, list(a), Policy())
    assert verdict.passed is True
    assert verdict.breached == []


def test_structural_change_fails_by_default():
    a = [_s(0, "shared line")]
    b = [_s(0, "shared line"), _s(1, "extra candidate step")]
    verdict, _ = run_check(a, b, Policy())
    assert verdict.passed is False
    assert "structural" in verdict.breached


def test_structural_change_allowed_when_flagged():
    a = [_s(0, "shared line", tokens_in=10)]
    b = [_s(0, "shared line", tokens_in=10), _s(1, "extra", tokens_in=1)]
    verdict, _ = run_check(a, b, Policy(allow_structural_change=True, max_token_delta_pct=200))
    assert verdict.passed is True


def test_cost_threshold_breach():
    a = [_s(0, "same content", cost=1.0)]
    b = [_s(0, "same content", cost=1.5)]  # +50%
    verdict, _ = run_check(a, b, Policy(max_cost_delta_pct=10))
    assert verdict.passed is False
    assert "cost" in verdict.breached


def test_untracked_metric_never_fails_cost():
    a = [_s(0, "same content")]  # no cost on either side
    b = [_s(0, "same content")]
    verdict = evaluate(run_check(a, b, Policy())[1], Policy(max_cost_delta_pct=0.0))
    assert "cost" not in verdict.breached


def test_exit_code_constants():
    assert (EXIT_PASS, EXIT_DRIFT, EXIT_ERROR) == (0, 1, 2)


def test_verdict_to_dict_shape():
    a = [_s(0, "x")]
    verdict, _ = run_check(a, list(a), Policy())
    d = verdict.to_dict()
    assert set(d) == {"passed", "reasons", "breached"}
