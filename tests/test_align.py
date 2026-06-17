"""Alignment: identical / insert / delete / reorder cases."""

from __future__ import annotations

from agentdiff.align import Op, align
from agentdiff.models import Step


def steps(*contents):
    return [Step(step=i, role="assistant", content=c) for i, c in enumerate(contents)]


def test_identical_all_match():
    a = steps("alpha apple", "bravo banana", "charlie cherry")
    pairs = align(a, list(a))
    assert [p.op for p in pairs] == [Op.MATCH, Op.MATCH, Op.MATCH]


def test_one_inserted_step():
    a = steps("alpha apple", "charlie cherry")
    b = steps("alpha apple", "bravo banana inserted here", "charlie cherry")
    pairs = align(a, b)
    assert sum(1 for p in pairs if p.op is Op.INSERT_B) == 1
    assert sum(1 for p in pairs if p.op is Op.MATCH) == 2


def test_one_deleted_step():
    a = steps("alpha apple", "bravo banana", "charlie cherry")
    b = steps("alpha apple", "charlie cherry")
    pairs = align(a, b)
    assert sum(1 for p in pairs if p.op is Op.DELETE_A) == 1
    assert sum(1 for p in pairs if p.op is Op.MATCH) == 2


def test_reorder_pairs_by_content_not_index():
    # Swapped middle steps should still pair to their true match.
    a = steps("the quick brown fox", "lazy dog sleeps", "end of run")
    b = steps("the quick brown fox", "lazy dog sleeps", "end of run")
    b[1], b[2] = b[2], b[1]
    b = [Step(step=i, role="assistant", content=s.content) for i, s in enumerate(b)]
    pairs = align(a, b)
    matched = {(p.a.content, p.b.content) for p in pairs if p.op is Op.MATCH}
    assert ("lazy dog sleeps", "lazy dog sleeps") in matched


def test_empty_inputs():
    assert align([], []) == []
