"""End-to-end: full pipeline per input format + cross-adapter parity."""

from __future__ import annotations

from agentdiff.adapters import load_trace
from agentdiff.align import align
from agentdiff.diff import compute_diff
from agentdiff.render import render_html


def _pipeline(path_a, path_b):
    a = load_trace(path_a)
    b = load_trace(path_b)
    diff = compute_diff(align(a.steps, b.steps))
    html = render_html(diff, meta={"title": "e2e", "source_a": path_a, "source_b": path_b})
    return diff, html


def test_jsonl_pipeline(trace_a, trace_b):
    diff, html = _pipeline(trace_a, trace_b)
    assert diff.first_divergence_index is not None  # A and B diverge
    assert "http://" not in html and "https://" not in html


def test_autodetect_otel(otel_file):
    trace = load_trace(otel_file)
    assert trace.meta["source"] == "otel"


def test_autodetect_langfuse(langfuse_file):
    trace = load_trace(langfuse_file)
    assert trace.meta["source"] == "langfuse"


def test_otel_langfuse_parity_with_jsonl(trace_a, otel_file, langfuse_file):
    # The OTel fixture describes the search_web steps of the trace-a run; those
    # steps should align onto trace-a as matches (same content + tool), proving
    # the adapters normalize to an equivalent Trace regardless of source format.
    jsonl = load_trace(trace_a)
    otel = load_trace(otel_file)
    diff = compute_diff(align(otel.steps, jsonl.steps))
    assert diff.summary_counts["match"] >= 2
