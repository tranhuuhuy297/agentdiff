"""Config discovery + flag merge for the golden-trace CI mode.

Reads ``agentdiff.toml`` / ``.agentdiff.toml`` (stdlib ``tomllib``, Python 3.11+)
discovered upward from the cwd, stopping at the filesystem root. CLI flags
override file values, which override built-in defaults.
"""

from __future__ import annotations

import os
import tomllib

DEFAULTS = {
    "max_cost_delta_pct": 10.0,
    "max_token_delta_pct": 20.0,
    "allow_structural_change": False,
}

_CONFIG_NAMES = ("agentdiff.toml", ".agentdiff.toml")


def discover_config(start: str | None = None) -> str | None:
    """Walk upward from ``start`` (cwd) looking for a config file."""
    current = os.path.abspath(start or os.getcwd())
    while True:
        for name in _CONFIG_NAMES:
            candidate = os.path.join(current, name)
            if os.path.isfile(candidate):
                return candidate
        parent = os.path.dirname(current)
        if parent == current:  # reached filesystem root
            return None
        current = parent


def load_config(path: str | None = None) -> dict:
    """Load config from ``path`` (or discovered), merged over defaults."""
    resolved = path or discover_config()
    config = dict(DEFAULTS)
    if resolved and os.path.isfile(resolved):
        with open(resolved, "rb") as fh:
            data = tomllib.load(fh)
        section = data.get("agentdiff", data) if isinstance(data, dict) else {}
        for key in DEFAULTS:
            if key in section:
                config[key] = section[key]
    return config


def merge_flags(config: dict, **flags) -> dict:
    """Overlay non-None CLI flags onto a config dict (flag > file > default)."""
    merged = dict(config)
    for key, value in flags.items():
        if value is not None:
            merged[key] = value
    return merged
