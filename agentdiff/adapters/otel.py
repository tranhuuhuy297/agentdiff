"""OpenTelemetry GenAI adapter — OTLP/JSON span export → Trace.

Maps the OTel GenAI semantic-convention attributes (``gen_ai.*``) onto ``Step``.
Reads an exported OTLP/JSON file (not a live collector) — file in, like every
other adapter. Tested against the OTel GenAI conventions as of 2026-06; tolerant
of missing attributes (they default via ``normalize_step``).
"""

from __future__ import annotations

import json
import os

from agentdiff.adapters.base import MAX_BYTES, finalize, normalize_step
from agentdiff.models import Step, Trace, TraceParseError


def _attrs_to_dict(attributes: list[dict]) -> dict:
    """OTLP attributes are ``[{key, value:{stringValue|intValue|...}}]``."""
    out: dict = {}
    for attr in attributes or []:
        key = attr.get("key")
        if not key:
            continue
        val = attr.get("value", {})
        out[key] = next(iter(val.values())) if isinstance(val, dict) and val else None
    return out


def _is_genai(attrs: dict, name: str) -> bool:
    return any(k.startswith("gen_ai.") for k in attrs) or name.startswith("gen_ai")


def _span_to_step(span: dict, index: int) -> Step:
    attrs = _attrs_to_dict(span.get("attributes", []))
    start = int(span.get("startTimeUnixNano") or 0)
    end = int(span.get("endTimeUnixNano") or 0)
    latency_ms = (end - start) / 1e6 if end > start else 0.0

    tool_name = attrs.get("gen_ai.tool.name")
    raw_args = attrs.get("gen_ai.tool.arguments") or attrs.get("gen_ai.tool.args")
    tool_args = None
    if raw_args:
        try:
            tool_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
        except (json.JSONDecodeError, TypeError):
            tool_args = {"raw": raw_args}

    role = attrs.get("gen_ai.operation.name") or ("tool" if tool_name else "assistant")
    content = (
        attrs.get("gen_ai.completion")
        or attrs.get("gen_ai.prompt")
        or span.get("name")
        or ""
    )

    return normalize_step(
        {
            "role": role,
            "content": content,
            "tool_name": tool_name,
            "tool_args": tool_args,
            "tokens_in": attrs.get("gen_ai.usage.input_tokens"),
            "tokens_out": attrs.get("gen_ai.usage.output_tokens"),
            "cost": attrs.get("gen_ai.usage.cost"),
            "latency_ms": latency_ms,
            "_otel_start": start,
        },
        index=index,
    )


def load_otel(path: str) -> Trace:
    """Load an OTLP/JSON span export into a ``Trace`` (GenAI spans only)."""
    if not os.path.exists(path):
        raise TraceParseError(f"file not found: {path}")
    if os.path.getsize(path) > MAX_BYTES:
        raise TraceParseError(f"file exceeds {MAX_BYTES} byte limit: {path}")

    with open(path, encoding="utf-8") as fh:
        try:
            doc = json.load(fh)
        except json.JSONDecodeError as exc:
            raise TraceParseError(f"invalid JSON: {exc.msg}", line_no=exc.lineno) from exc

    spans: list[dict] = []
    for resource in doc.get("resourceSpans", []):
        for scope in resource.get("scopeSpans", []):
            for span in scope.get("spans", []):
                attrs = _attrs_to_dict(span.get("attributes", []))
                if _is_genai(attrs, span.get("name", "")):
                    spans.append(span)

    spans.sort(key=lambda s: int(s.get("startTimeUnixNano") or 0))
    steps = [_span_to_step(span, i) for i, span in enumerate(spans)]
    return finalize(steps, meta={"source": "otel", "path": path})
