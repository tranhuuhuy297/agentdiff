"""JSONL adapter: load, defaults, error line numbers."""

from __future__ import annotations

import pytest

from agentdiff.adapters.jsonl import load_jsonl
from agentdiff.models import TraceParseError


def test_loads_example(trace_a):
    trace = load_jsonl(trace_a)
    assert len(trace.steps) == 4
    assert trace.meta["source"] == "jsonl"
    assert trace.steps[0].role == "user"
    assert trace.steps[1].tool_name == "search_web"


def test_numeric_defaults(tmp_path):
    f = tmp_path / "t.jsonl"
    f.write_text('{"step": 0, "role": "assistant", "content": "hi"}\n')
    trace = load_jsonl(str(f))
    assert trace.steps[0].tokens_in == 0
    assert trace.steps[0].cost == 0.0
    assert trace.steps[0].tool_name is None


def test_blank_lines_skipped(tmp_path):
    f = tmp_path / "t.jsonl"
    f.write_text('{"step": 0, "role": "user", "content": "a"}\n\n   \n')
    assert len(load_jsonl(str(f)).steps) == 1


def test_bad_line_reports_line_number(tmp_path):
    f = tmp_path / "t.jsonl"
    f.write_text('{"step": 0, "role": "user"}\n{not json}\n')
    with pytest.raises(TraceParseError) as exc:
        load_jsonl(str(f))
    assert exc.value.line_no == 2


def test_out_of_order_steps_sorted(tmp_path):
    f = tmp_path / "t.jsonl"
    f.write_text('{"step": 2, "role": "a"}\n{"step": 0, "role": "b"}\n{"step": 1, "role": "c"}\n')
    trace = load_jsonl(str(f))
    assert [s.step for s in trace.steps] == [0, 1, 2]
    assert trace.meta.get("reordered") is True


def test_missing_file():
    with pytest.raises(TraceParseError):
        load_jsonl("/no/such/file.jsonl")
