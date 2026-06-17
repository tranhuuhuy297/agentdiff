"""Canonical in-memory trace model — the spine of agentdiff.

Every adapter produces a ``Trace``; every consumer (align, diff, render, ci)
reads one. Keep this shape stable: changing it cascades through the whole tool.
Uses stdlib dataclasses (no runtime dep) with explicit normalization in the
adapter layer rather than a schema framework (KISS).
"""

from __future__ import annotations

from dataclasses import dataclass, field


class TraceParseError(Exception):
    """Raised when a trace file cannot be parsed.

    Carries the offending line number (1-based, ``None`` if not line-scoped)
    so callers can point users at the exact bad input.
    """

    def __init__(self, reason: str, line_no: int | None = None) -> None:
        self.reason = reason
        self.line_no = line_no
        where = f" (line {line_no})" if line_no is not None else ""
        super().__init__(f"{reason}{where}")


@dataclass
class Step:
    """One step in an agent trajectory.

    Only ``step`` and ``role`` are conceptually required; everything else
    defaults so dirty real-world exports still load. ``extra`` carries
    adapter-specific passthrough that align/diff ignore.
    """

    step: int
    role: str = ""
    content: str = ""
    tool_name: str | None = None
    tool_args: dict | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    cost: float = 0.0
    latency_ms: float = 0.0
    extra: dict = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.tokens_in + self.tokens_out

    @property
    def is_tool_call(self) -> bool:
        return bool(self.tool_name)

    def label(self) -> str:
        """Short human label for terminal/summary rendering."""
        if self.tool_name:
            return f"{self.role or 'step'} · {self.tool_name}"
        return self.role or "step"


@dataclass
class Trace:
    """An ordered list of steps plus provenance metadata."""

    steps: list[Step] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.steps)
