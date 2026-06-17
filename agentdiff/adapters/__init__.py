"""Adapter registry + format dispatch.

``get_loader(name)`` resolves a format name to its loader; ``detect_format``
sniffs a path by extension + content signature. JSONL is the default.
"""

from __future__ import annotations

import json
import os

from agentdiff.adapters.jsonl import load_jsonl
from agentdiff.adapters.langfuse import load_langfuse
from agentdiff.adapters.otel import load_otel
from agentdiff.models import Trace, TraceParseError

_LOADERS = {
    "jsonl": load_jsonl,
    "otel": load_otel,
    "langfuse": load_langfuse,
}

__all__ = ["load_jsonl", "load_otel", "load_langfuse", "get_loader", "detect_format", "load_trace"]


def get_loader(name: str):
    """Return the loader callable for a format name."""
    try:
        return _LOADERS[name]
    except KeyError:
        raise TraceParseError(
            f"unknown format '{name}'; expected one of {sorted(_LOADERS)}"
        ) from None


def detect_format(path: str) -> str:
    """Detect format by extension, falling back to a content sniff for ``.json``."""
    lower = path.lower()
    if lower.endswith(".jsonl") or lower.endswith(".ndjson"):
        return "jsonl"
    if lower.endswith(".json"):
        return _sniff_json(path)
    # Unknown extension: peek at the content.
    return _sniff_json(path) if os.path.exists(path) else "jsonl"


def _sniff_json(path: str) -> str:
    """Distinguish OTel vs Langfuse vs JSONL by signature keys."""
    try:
        with open(path, encoding="utf-8") as fh:
            head = fh.read(65536)
    except OSError:
        return "jsonl"
    stripped = head.lstrip()
    if not stripped.startswith("["):
        # A single JSON object — could be OTel or Langfuse.
        try:
            doc = json.loads(head)
        except json.JSONDecodeError:
            return "jsonl"
        if isinstance(doc, dict):
            if "resourceSpans" in doc:
                return "otel"
            if "observations" in doc or (isinstance(doc.get("data"), dict)):
                return "langfuse"
    return "jsonl"


def load_trace(path: str, fmt: str | None = None) -> Trace:
    """Load a trace, auto-detecting the format unless ``fmt`` is given."""
    return get_loader(fmt or detect_format(path))(path)
