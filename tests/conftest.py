"""Shared fixtures: paths to the bundled example traces + helpers."""

from __future__ import annotations

import os

import pytest

EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(__file__)), "examples")


@pytest.fixture
def examples_dir() -> str:
    return EXAMPLES


@pytest.fixture
def trace_a() -> str:
    return os.path.join(EXAMPLES, "trace-a.jsonl")


@pytest.fixture
def trace_b() -> str:
    return os.path.join(EXAMPLES, "trace-b.jsonl")


@pytest.fixture
def golden() -> str:
    return os.path.join(EXAMPLES, "golden-trace.jsonl")


@pytest.fixture
def otel_file() -> str:
    return os.path.join(EXAMPLES, "trace-otel.json")


@pytest.fixture
def langfuse_file() -> str:
    return os.path.join(EXAMPLES, "trace-langfuse.json")
