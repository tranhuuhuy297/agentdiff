"""Similarity scorers: determinism + tool-name weighting."""

from __future__ import annotations

from agentdiff.models import Step
from agentdiff.similarity import get_scorer, lexical_similarity


def _step(content="", tool=None):
    return Step(step=0, role="assistant", content=content, tool_name=tool)


def test_identical_content_scores_high():
    s = _step("call the weather api")
    assert lexical_similarity(s, _step("call the weather api")) > 0.95


def test_deterministic():
    a, b = _step("alpha beta"), _step("beta gamma")
    assert lexical_similarity(a, b) == lexical_similarity(a, b)


def test_tool_match_raises_score():
    base_a = _step("do thing", tool="search")
    same_tool = _step("do thing", tool="search")
    diff_tool = _step("do thing", tool="other")
    assert lexical_similarity(base_a, same_tool) > lexical_similarity(base_a, diff_tool)


def test_tool_mismatch_penalized_vs_no_tool():
    # Same content; a tool mismatch should score below a pure-content match.
    content_only = lexical_similarity(_step("x y z"), _step("x y z"))
    tool_mismatch = lexical_similarity(_step("x y z", tool="a"), _step("x y z", tool="b"))
    assert tool_mismatch < content_only


def test_get_scorer_defaults_lexical():
    assert get_scorer(False) is lexical_similarity
