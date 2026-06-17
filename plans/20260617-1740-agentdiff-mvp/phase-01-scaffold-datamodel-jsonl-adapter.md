# Phase 01 — Scaffold + Data Model + JSONL Adapter

## Context Links
- Overview: [plan.md](plan.md)
- Next: [phase-02-step-alignment-algorithm.md](phase-02-step-alignment-algorithm.md)

## Overview
- **Priority:** P1 (blocks everything)
- **Status:** pending
- **Description:** Stand up the repo, packaging, lint/test config, the canonical in-memory
  trace model, and the first input adapter (minimal JSONL). After this phase you can load and
  validate a trace file into `Trace(list[Step])`.

## Key Insights
- The data model is the spine of the whole tool — every adapter writes it, every consumer reads it.
  Lock it now; changing it later cascades through alignment, diff, render.
- Use stdlib `dataclasses` (KISS) over pydantic for MVP: no runtime dep, fast, enough validation
  for a CLI. Validation = explicit checks raising `TraceParseError`, not a schema framework.
- JSONL is line-delimited: stream-parse so a single bad line reports its line number and the rest
  can still load (resilience matters for real-world dirty exports).

## Requirements
**Functional**
- Parse a `.jsonl` file where each line is one step object.
- Step schema (all fields optional except `step`,`role`): `{step:int, role:str, content:str,
  tool_name:str|None, tool_args:dict|None, tokens_in:int, tokens_out:int, cost:float, latency_ms:float}`.
- Missing numeric fields default to `0`; missing optional strings default to `None`/`""`.
- Sort steps by `step` index; detect duplicate/out-of-order indices → warn, do not crash.

**Non-functional**
- No third-party runtime dep for this phase except the CLI/test/lint tooling skeleton.
- Adapter is pure parse (file path/string in → `Trace` out), no global state.

## Architecture
```
file.jsonl --(adapters/jsonl.py: load_jsonl)--> Trace
                                                 ├── meta: dict (source, path)
                                                 └── steps: list[Step]  (dataclass)
```
- `models.py` defines `Step`, `Trace`, `TraceParseError`. No I/O here.
- `adapters/base.py` defines the adapter contract: `load(path) -> Trace` + field-normalization helpers
  shared across all adapters (DRY — OTel/Langfuse reuse `normalize_step`).
- `adapters/jsonl.py` implements the JSONL loader on that contract.

## Data Flow
Enters: raw bytes/lines from a file path. Transforms: JSON parse → field normalize → `Step` →
sort/dedupe → `Trace`. Exits: a validated `Trace` object (no rendering, no diffing yet).

## Related Code Files
**Create**
- `pyproject.toml` — PEP 621 metadata, hatchling build, `[project.optional-dependencies]`
  `semantic=[fastembed]`, `dev=[pytest,ruff]`. Entry point `agentdiff = "agentdiff.cli:app"` (stub).
- `agentdiff/__init__.py` — version export.
- `agentdiff/models.py` — `Step`, `Trace`, `TraceParseError` (≤120 lines).
- `agentdiff/adapters/__init__.py`
- `agentdiff/adapters/base.py` — adapter protocol + `normalize_step`, `coerce_number` helpers.
- `agentdiff/adapters/jsonl.py` — `load_jsonl(path) -> Trace`.
- `examples/trace-a.jsonl`, `examples/trace-b.jsonl` — small hand-written sample traces (diverge mid-run).
- `ruff.toml` (or `[tool.ruff]` in pyproject) — line length, rule set.
- `.gitignore`, `LICENSE` (MIT — OSS), `README.md` (stub with one-liner + quickstart placeholder).

**Modify** — none (greenfield).
**Delete** — none.

## Implementation Steps
1. `git init`; create directory tree per repo structure; add `.gitignore` (Python), MIT `LICENSE`.
2. Write `pyproject.toml`: name, version `0.0.1`, Python `>=3.11` (chosen so P6 can use stdlib
   `tomllib` with no backport dep — see P7 Open Questions; revisit only if 3.10 support is required),
   deps `typer`, optional extras `semantic`/`dev`, console-script entry point (CLI stub so install works).
3. Implement `models.py`: `@dataclass Step` with the 9 fields + defaults; `@dataclass Trace`
   with `steps: list[Step]` and `meta: dict`; `TraceParseError(line_no, reason)`.
4. Implement `adapters/base.py`: `coerce_number(v, default)` (None/str→number safe), `normalize_step(raw)`
   mapping a raw dict → `Step`, and an `Adapter` Protocol with `load(path)->Trace`.
5. Implement `adapters/jsonl.py`: open file, enumerate lines, skip blanks, `json.loads` each,
   `normalize_step`, collect; on a bad line raise/collect `TraceParseError` with line number;
   sort by `step`; return `Trace(meta={"source":"jsonl","path":path})`.
6. Author two example traces that share a prefix then diverge (different tool call) — drives later phases.
7. Add a smoke test `tests/test_jsonl_adapter.py`: load examples, assert step count, field defaults,
   bad-line error carries line number.
8. Run `ruff check .` and `pytest` — both green.

## Todo List
- [ ] Repo tree + git init + LICENSE + .gitignore
- [ ] pyproject.toml with extras + entry point
- [ ] models.py (Step, Trace, TraceParseError)
- [ ] adapters/base.py (Protocol + normalizers)
- [ ] adapters/jsonl.py (load_jsonl)
- [ ] examples/trace-a.jsonl + trace-b.jsonl
- [ ] tests/test_jsonl_adapter.py
- [ ] ruff + pytest green

## Success Criteria
- `pip install -e .` succeeds; `agentdiff --help` runs (even if stub).
- `python -c "from agentdiff.adapters.jsonl import load_jsonl; print(len(load_jsonl('examples/trace-a.jsonl').steps))"` prints step count.
- Bad line → `TraceParseError` naming the line number; good lines still load.
- `pytest` green, `ruff check .` clean.

## Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Data model too narrow, churns later | Med | High | Keep `Step.extra: dict` field for adapter-specific passthrough; align/diff ignore unknown keys |
| Dirty real-world JSONL crashes loader | Med | Med | Per-line try/except, report line number, continue where safe |
| dataclass vs pydantic regret | Low | Med | Normalization centralized in base.py — swap internals without touching model shape |

## Backwards Compatibility / Rollback
- Greenfield: nothing to migrate. Rollback = delete branch.
- Schema is the public contract → version it in README; additive changes only after release.

## Security Considerations
- Untrusted input files: `json.loads` is safe; never `eval`. Cap line size / file size guard to avoid
  pathological memory blowup (add `max_bytes` guard, default generous).

## Next Steps
- Unblocks P2 (alignment consumes `list[Step]`) and P5 (adapters reuse `base.py`).

## Open Questions
- Should `step` be required, or auto-index by line order if absent? (Lean: auto-index fallback.)
- Multi-line content with embedded newlines in JSONL — rely on JSON escaping (yes) vs allow NDJSON only.
