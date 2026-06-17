"""Langfuse adapter — trace JSON export → Trace.

Flattens a Langfuse trace's nested observations (generations/spans/tool calls)
into ordered steps, reusing the usage + cost fields Langfuse already computes.
Defensive ``.get()`` mapping tolerates schema drift across Langfuse versions.
"""

from __future__ import annotations

import json
import os

from agentdiff.adapters.base import MAX_BYTES, finalize, normalize_step
from agentdiff.models import Step, Trace, TraceParseError

_TYPE_TO_ROLE = {"GENERATION": "assistant", "SPAN": "span", "EVENT": "event", "TOOL": "tool"}


def _observation_to_step(obs: dict, index: int) -> Step:
    usage = obs.get("usage") or {}
    obs_type = (obs.get("type") or "").upper()

    tool_name = obs.get("toolName") or obs.get("tool_name")
    tool_args = obs.get("input") if tool_name else None
    if tool_args is not None and not isinstance(tool_args, dict):
        tool_args = {"value": tool_args}

    content = obs.get("output") or obs.get("input") or obs.get("name") or ""
    if isinstance(content, (dict, list)):
        content = json.dumps(content, ensure_ascii=False)

    return normalize_step(
        {
            "role": _TYPE_TO_ROLE.get(obs_type, obs_type.lower() or "observation"),
            "content": str(content),
            "tool_name": tool_name,
            "tool_args": tool_args,
            "tokens_in": usage.get("input") or usage.get("promptTokens"),
            "tokens_out": usage.get("output") or usage.get("completionTokens"),
            "cost": obs.get("calculatedTotalCost") or obs.get("totalCost"),
            "latency_ms": obs.get("latency") or obs.get("latencyMs"),
            "_lf_start": obs.get("startTime") or "",
        },
        index=index,
    )


def load_langfuse(path: str) -> Trace:
    """Load a Langfuse trace export into a ``Trace``."""
    if not os.path.exists(path):
        raise TraceParseError(f"file not found: {path}")
    if os.path.getsize(path) > MAX_BYTES:
        raise TraceParseError(f"file exceeds {MAX_BYTES} byte limit: {path}")

    with open(path, encoding="utf-8") as fh:
        try:
            doc = json.load(fh)
        except json.JSONDecodeError as exc:
            raise TraceParseError(f"invalid JSON: {exc.msg}", line_no=exc.lineno) from exc

    observations = doc.get("observations")
    if observations is None and isinstance(doc.get("data"), dict):
        observations = doc["data"].get("observations")
    if observations is None:
        raise TraceParseError("no 'observations' array in Langfuse export")

    # Order by start time; fall back to given order when timestamps absent.
    observations = sorted(observations, key=lambda o: o.get("startTime") or "")
    steps = [_observation_to_step(obs, i) for i, obs in enumerate(observations)]
    return finalize(steps, meta={"source": "langfuse", "path": path})
