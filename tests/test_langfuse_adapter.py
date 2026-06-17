"""Langfuse adapter: observation flattening, usage/cost mapping, ordering."""

from __future__ import annotations

import pytest

from agentdiff.adapters.langfuse import load_langfuse
from agentdiff.models import TraceParseError


def test_loads_observations(langfuse_file):
    trace = load_langfuse(langfuse_file)
    assert trace.meta["source"] == "langfuse"
    assert len(trace.steps) == 3


def test_maps_usage_cost_and_tool(langfuse_file):
    trace = load_langfuse(langfuse_file)
    gen = trace.steps[0]
    assert gen.tokens_in == 40
    assert gen.tokens_out == 22
    assert gen.cost == 0.0009
    tool_step = trace.steps[1]
    assert tool_step.tool_name == "search_web"
    assert tool_step.tool_args == {"query": "Hanoi weather today"}


def test_ordered_by_start_time(langfuse_file):
    trace = load_langfuse(langfuse_file)
    starts = [s.extra.get("_lf_start") for s in trace.steps]
    assert starts == sorted(starts)


def test_missing_observations_raises(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text('{"id": "x"}')
    with pytest.raises(TraceParseError):
        load_langfuse(str(f))
