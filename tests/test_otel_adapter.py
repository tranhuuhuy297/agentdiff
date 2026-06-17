"""OTel GenAI adapter: attribute mapping, ordering, latency."""

from __future__ import annotations

from agentdiff.adapters.otel import load_otel


def test_loads_genai_spans(otel_file):
    trace = load_otel(otel_file)
    assert trace.meta["source"] == "otel"
    assert len(trace.steps) == 2


def test_maps_tokens_and_tool(otel_file):
    trace = load_otel(otel_file)
    first = trace.steps[0]
    assert first.tokens_in == 40
    assert first.tokens_out == 22
    assert first.tool_name == "search_web"
    assert first.tool_args == {"query": "Hanoi weather today"}


def test_latency_from_span_duration(otel_file):
    trace = load_otel(otel_file)
    # (1480000000 - 1000000000) / 1e6 = 480 ms
    assert trace.steps[0].latency_ms == 480.0


def test_ordered_by_start_time(otel_file):
    trace = load_otel(otel_file)
    starts = [s.extra.get("_otel_start") for s in trace.steps]
    assert starts == sorted(starts)
