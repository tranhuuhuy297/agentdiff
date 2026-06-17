"""CLI surface via typer's CliRunner: exit codes + file output."""

from __future__ import annotations

import json
import os

from typer.testing import CliRunner

from agentdiff.cli import app

runner = CliRunner()


def test_diff_writes_html(trace_a, trace_b, tmp_path):
    out = tmp_path / "r.html"
    result = runner.invoke(app, ["diff", trace_a, trace_b, "--no-open", "--out", str(out)])
    assert result.exit_code == 0
    assert out.exists()
    assert "http://" not in out.read_text()


def test_diff_terminal(trace_a, trace_b):
    result = runner.invoke(app, ["diff", trace_a, trace_b, "--terminal"])
    assert result.exit_code == 0


def test_diff_bad_path_exits_2(trace_a):
    result = runner.invoke(app, ["diff", trace_a, "/no/such.jsonl", "--no-open"])
    assert result.exit_code == 2


def test_check_identical_passes(golden, tmp_path):
    out = tmp_path / "v.json"
    result = runner.invoke(app, ["check", golden, "--golden", golden, "--json", str(out)])
    assert result.exit_code == 0
    payload = json.loads(out.read_text())
    assert payload["verdict"]["passed"] is True


def test_check_drift_exits_1(golden, trace_b):
    result = runner.invoke(app, ["check", trace_b, "--golden", golden])
    assert result.exit_code == 1


def test_golden_copies_file(trace_a, tmp_path):
    out = tmp_path / "golden.jsonl"
    result = runner.invoke(app, ["golden", trace_a, "--out", str(out)])
    assert result.exit_code == 0
    assert out.exists()
    assert os.path.getsize(out) == os.path.getsize(trace_a)


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "agentdiff" in result.stdout
