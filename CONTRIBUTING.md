# Contributing to agentdiff

Thanks for your interest! agentdiff is a small, focused tool — contributions that
keep it lean and local-first are very welcome.

## Dev setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest          # run the suite
ruff check .    # lint
```

Requires Python 3.11+.

## Project layout

```
agentdiff/
├── models.py        # canonical Step / Trace (the spine — change carefully)
├── adapters/        # one file per input format; reuse base.normalize_step
├── similarity.py    # per-step scorers (lexical default, semantic opt-in)
├── align.py         # Needleman–Wunsch alignment (pure)
├── diff.py          # DiffResult / deltas (pure, serializable)
├── render/          # HTML viewer template + terminal rendering
├── ci.py            # golden-trace policy + verdict
├── config.py        # agentdiff.toml loading
└── cli.py           # typer commands (I/O lives here)
```

## Adding an input adapter

1. Create `agentdiff/adapters/<format>.py` with `load_<format>(path) -> Trace`,
   mapping fields through `agentdiff.adapters.base.normalize_step`.
2. Register it in `agentdiff/adapters/__init__.py` (`_LOADERS` + `detect_format`).
3. Add a small fixture under `examples/` and a test under `tests/`.

## Conventions

- Keep modules under ~200 lines; prefer pure functions; isolate I/O to adapters + cli.
- The rendered HTML must make **zero external requests** — a test enforces this.
- Lexical alignment stays the default (no network, no API key). Semantic stays opt-in.
- Conventional-commit messages; run `ruff` and `pytest` before opening a PR.
