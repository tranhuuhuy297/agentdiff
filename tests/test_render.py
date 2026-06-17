"""Rendering: HTML has deltas + no external refs; terminal doesn't raise."""

from __future__ import annotations

from agentdiff.align import align
from agentdiff.diff import compute_diff
from agentdiff.models import Step
from agentdiff.render import render_html, render_terminal


def _diff():
    a = [Step(step=0, role="user", content="hello"), Step(step=1, role="assistant", content="world", tokens_in=10)]
    b = [Step(step=0, role="user", content="hello"), Step(step=1, role="assistant", content="worlds", tokens_in=15)]
    return compute_diff(align(a, b))


def test_html_has_no_external_refs():
    html = render_html(_diff(), meta={"title": "t", "source_a": "a", "source_b": "b"})
    assert "http://" not in html
    assert "https://" not in html


def test_html_embeds_diff_json_and_title():
    html = render_html(_diff(), meta={"title": "my-diff", "source_a": "a.jsonl", "source_b": "b.jsonl"})
    assert "my-diff" in html
    assert "first_divergence_index" in html
    assert "diff-data" in html


def test_html_escapes_script_in_content():
    a = [Step(step=0, role="user", content="</script><script>alert(1)</script>")]
    html = render_html(compute_diff(align(a, list(a))))
    # The raw closing-script sequence must not appear unescaped in the blob.
    assert "</script><script>alert(1)" not in html


def test_terminal_render_runs():
    render_terminal(_diff())  # should not raise
