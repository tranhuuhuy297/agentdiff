"""Config: toml load + flag-merge precedence (CLI > file > default)."""

from __future__ import annotations

from agentdiff.config import DEFAULTS, load_config, merge_flags


def test_defaults_when_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = load_config()
    assert cfg["max_cost_delta_pct"] == DEFAULTS["max_cost_delta_pct"]


def test_loads_toml_section(tmp_path):
    f = tmp_path / "agentdiff.toml"
    f.write_text('[agentdiff]\nmax_cost_delta_pct = 5.0\nallow_structural_change = true\n')
    cfg = load_config(str(f))
    assert cfg["max_cost_delta_pct"] == 5.0
    assert cfg["allow_structural_change"] is True


def test_discovers_upward(tmp_path, monkeypatch):
    (tmp_path / "agentdiff.toml").write_text('[agentdiff]\nmax_token_delta_pct = 1.0\n')
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    monkeypatch.chdir(sub)
    cfg = load_config()
    assert cfg["max_token_delta_pct"] == 1.0


def test_flag_overrides_file():
    cfg = {"max_cost_delta_pct": 5.0, "allow_structural_change": False}
    merged = merge_flags(cfg, max_cost_delta_pct=99.0, allow_structural_change=None)
    assert merged["max_cost_delta_pct"] == 99.0  # flag wins
    assert merged["allow_structural_change"] is False  # None ignored
