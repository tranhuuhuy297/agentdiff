"""JSONL adapter — one JSON step object per line.

Stream-parses so a single bad line reports its line number while valid lines
still load (resilience for dirty real-world exports).
"""

from __future__ import annotations

import json
import os

from agentdiff.adapters.base import MAX_BYTES, finalize, normalize_step
from agentdiff.models import Step, Trace, TraceParseError


def load_jsonl(path: str) -> Trace:
    """Load a ``.jsonl`` trace file into a ``Trace``."""
    if not os.path.exists(path):
        raise TraceParseError(f"file not found: {path}")
    if os.path.getsize(path) > MAX_BYTES:
        raise TraceParseError(f"file exceeds {MAX_BYTES} byte limit: {path}")

    steps: list[Step] = []
    with open(path, encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise TraceParseError(f"invalid JSON: {exc.msg}", line_no=line_no) from exc
            if not isinstance(raw, dict):
                raise TraceParseError("each line must be a JSON object", line_no=line_no)
            steps.append(normalize_step(raw, index=line_no - 1))

    return finalize(steps, meta={"source": "jsonl", "path": path})
