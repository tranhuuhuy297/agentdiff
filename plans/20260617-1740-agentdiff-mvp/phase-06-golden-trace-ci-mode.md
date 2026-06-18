# Phase 06 — Golden-Trace CI Regression Mode (killer feature)

## Context Links
- Overview: [plan.md](plan.md)
- Prev: [phase-05-otel-langfuse-adapters.md](phase-05-otel-langfuse-adapters.md)
- Next: [phase-07-tests-packaging-release.md](phase-07-tests-packaging-release.md)

## Overview
- **Priority:** P2 (the recurring-use angle LangSmith under-serves; the retention hook)
- **Status:** done
- **Description:** Save a reference ("golden") trajectory and diff every new run against it in CI;
  exit non-zero when the trajectory drifts beyond a configured threshold. Pure CLI, no service.

## Key Insights
- This reuses the entire P2→P3 pipeline; the only new logic is: (a) a threshold policy over a
  `DiffResult`, and (b) process exit codes + machine-readable output for CI. No re-implementation (DRY).
- "Drift" is multi-dimensional — structural (any insert/delete/substitute? where's first divergence?)
  and quantitative (Δtokens/Δcost/Δlatency beyond %). Let users threshold on the dimensions they care
  about; default to a sane structural+cost policy.
- CI ergonomics: deterministic, no browser, no network on default path; emit a one-line verdict + a
  JSON report artifact; exit 0 (pass) / 1 (drift) / 2 (error).

## Requirements
**Functional**
- `agentdiff check NEW --golden GOLDEN [--config FILE] [--max-cost-delta-pct N]
  [--max-token-delta-pct N] [--allow-structural-change] [--json OUT] [--report-html OUT]`.
- Load both via existing adapters → align → `compute_diff` → evaluate against thresholds → verdict.
- Default policy: fail if any structural change (insert/delete/substitute present) OR cost delta >
  threshold OR token delta > threshold. All thresholds overridable via flags or a config file
  (`agentdiff.toml`/`.agentdiff.toml`).
- Output: human one-liner to stderr, optional `--json` machine report, optional `--report-html` for
  the failing diff. Exit code: 0 pass / 1 drift / 2 usage-or-load error.
- `agentdiff golden NEW --out path` convenience to save a run as the golden reference (copy + note).

**Non-functional**
- Deterministic on the lexical path (semantic alignment is non-default in CI; if used, pin model).
- Zero network on default path; suitable for offline CI runners.

## Architecture
```
ci.py: check(new, golden, policy)
   load(golden), load(new) ─> align() ─> compute_diff() ─> evaluate(diff, policy) ─> Verdict
                                                                       │
   policy = from flags + config file (config.py)                      ▼
   Verdict{passed, reasons[], breached_metrics[]} ─> exit code + stderr line + optional json/html
```
- `agentdiff/ci.py` — `Policy` dataclass, `evaluate(diff, policy) -> Verdict`, `run_check(...)` (≤170 lines).
- `agentdiff/config.py` — load `agentdiff.toml` via stdlib `tomllib` (3.11+); merge with CLI flags.
- `cli.py` — add `check` and `golden` commands (orchestration only).

## Data Flow
Enters: a new run file + golden file + policy (flags/config). Transforms: load both → diff →
evaluate thresholds → verdict. Exits: process exit code + stderr verdict line (+ optional json/html
artifacts). Pure evaluation in `ci.evaluate`; I/O confined to cli + config loader.

## Related Code Files
**Create**
- `agentdiff/ci.py` — `Policy`, `Verdict`, `evaluate`, `run_check`.
- `agentdiff/config.py` — `load_config(path|discover) -> dict`, flag-merge helper.
- `tests/test_ci.py` — pass (identical), fail-structural, fail-cost-threshold, threshold override,
  exit codes (0/1/2), `--json` shape.
- `tests/test_config.py` — toml load + precedence (CLI flag overrides file overrides default).
- `examples/golden-trace.jsonl`, `examples/agentdiff.toml` — sample config.
- `.github/workflows/agentdiff-check-example.yml` — documented usage snippet for adopters' CI.

**Modify**
- `agentdiff/cli.py` — register `check` + `golden` commands.
- `README.md` — "Golden-trace regression in CI" section with copy-paste workflow.

**Delete** — none.

## Implementation Steps
1. `config.py`: discover `agentdiff.toml`/`.agentdiff.toml` upward from cwd; parse with `tomllib`;
   return defaults if absent; helper to overlay CLI flags (flag > file > default).
2. `ci.py`: `Policy` (max_cost_delta_pct, max_token_delta_pct, allow_structural_change, dims to check);
   `evaluate(diff, policy)` → `Verdict(passed, reasons, breached)`; honor `available=False` (don't fail
   on an untracked metric).
3. Percentage deltas computed vs golden totals; guard divide-by-zero (golden total 0 → use absolute or
   skip with reason).
4. `run_check`: load golden+new → align → diff → evaluate → emit stderr verdict; write `--json`/
   `--report-html` if requested; return exit code (0/1/2).
5. Add `check` + `golden` typer commands; map `run_check` return to `raise typer.Exit(code)`.
6. Tests: identical→exit 0; inserted step + `--allow-structural-change` off → exit 1 with reason;
   cost +50% over 10% threshold → exit 1; load error → exit 2; `--json` parses + lists breaches.
7. Author the example GitHub Actions workflow (runs `agentdiff check` on a fixture).
8. `ruff` + `pytest` green.

## Todo List
- [x] config.py (tomllib discover + flag merge precedence)
- [x] ci.py Policy/Verdict/evaluate (honor available=False, divide-by-zero guard)
- [x] run_check (load→align→diff→evaluate→exit code + artifacts)
- [x] cli: check + golden commands mapping to typer.Exit
- [x] tests: pass/fail-structural/fail-cost/exit-codes/json + config precedence
- [x] example workflow + agentdiff.toml + golden fixture
- [x] README CI section
- [x] ruff + pytest green

## Success Criteria
- `agentdiff check new.jsonl --golden golden.jsonl` exits 0 when identical, 1 when drifted past policy,
  2 on load/usage error.
- Thresholds honored from both CLI flags and `agentdiff.toml`, with CLI winning.
- `--json` emits a parseable verdict listing breached dimensions + reasons.
- Untracked metric (cost absent) never causes a false failure.
- Example GHA workflow runs the check and gates on its exit code.

## Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Flaky CI from semantic-alignment nondeterminism | Med | High | Default = lexical (deterministic); if `--semantic` in CI, pin model + document flakiness risk |
| Divide-by-zero on % delta when golden metric is 0 | Med | Med | Guard: fall back to absolute threshold or skip dim with explicit reason |
| Too-strict default policy → noisy adoption | Med | Med | Default structural-fail but easy `--allow-structural-change`; document tuning; ship example config |
| Exit-code semantics misused by adopters | Low | Med | Document 0/1/2 contract prominently; test pins each code |

## Backwards Compatibility / Rollback
- New commands; existing `diff` command untouched. Config file optional (absent → defaults).
- `Verdict` JSON shape is a public contract for CI parsers → version + additive-only.
- Rollback: drop `check`/`golden` commands; pipeline + `diff` remain intact.

## Security Considerations
- Config discovery walks parent dirs — stop at filesystem root / repo boundary; don't read configs
  outside the project unexpectedly. Same untrusted-input guards as adapters.

## Next Steps
- Final hardening + release in P7 (tests matrix, packaging, PyPI, demo GIF, docs).

## Open Questions
- Default thresholds (cost % / token %) — pick conservative starting values; calibrate with examples.
- Should `check` support diffing a new run against a *directory* of goldens (suite mode)? (Defer — YAGNI.)
