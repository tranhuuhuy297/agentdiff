"""Diff/delta computation: divergence, B−A arithmetic, availability."""

from __future__ import annotations

import json

from agentdiff.align import align
from agentdiff.diff import compute_diff
from agentdiff.models import Step


def _s(i, content="x", **kw):
    return Step(step=i, role="assistant", content=content, **kw)


def test_identical_no_divergence_zero_deltas():
    a = [_s(0, "hello world", tokens_in=10), _s(1, "second step", tokens_in=5)]
    diff = compute_diff(align(a, list(a)))
    assert diff.first_divergence_index is None
    assert diff.deltas["total_tokens"].value == 0


def test_inserted_step_delta_and_divergence():
    a = [_s(0, "shared opening line")]
    b = [_s(0, "shared opening line"), _s(1, "brand new candidate step", tokens_in=12, tokens_out=8)]
    diff = compute_diff(align(a, b))
    assert diff.first_divergence_index == 1
    assert diff.deltas["total_tokens"].value == 20  # B−A


def test_cost_unavailable_when_all_zero():
    a = [_s(0, "no cost tracked here")]
    diff = compute_diff(align(a, list(a)))
    assert diff.deltas["cost"].available is False


def test_tool_call_counting():
    a = [_s(0, "plan"), _s(1, "call", tool_name="search")]
    b = [_s(0, "plan"), _s(1, "call", tool_name="search"), _s(2, "call2", tool_name="fetch")]
    diff = compute_diff(align(a, b))
    assert diff.totals_a.tool_calls == 1
    assert diff.totals_b.tool_calls == 2
    assert diff.deltas["tool_calls"].value == 1


def test_to_dict_json_serializable():
    a = [_s(0, "alpha"), _s(1, "beta", tool_name="t", tool_args={"k": "v"})]
    b = [_s(0, "alpha"), _s(1, "beta changed", tool_name="t", tool_args={"k": "v2"})]
    diff = compute_diff(align(a, b))
    dumped = json.dumps(diff.to_dict())
    assert "first_divergence_index" in dumped
