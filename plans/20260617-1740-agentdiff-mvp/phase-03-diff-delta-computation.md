# Phase 03 — Diff + Delta Computation

## Context Links
- Overview: [plan.md](plan.md)
- Prev: [phase-02-step-alignment-algorithm.md](phase-02-step-alignment-algorithm.md)
- Next: [phase-04-html-viewer-cli.md](phase-04-html-viewer-cli.md)

## Overview
- **Priority:** P1
- **Status:** pending
- **Description:** Turn aligned pairs into a structured `DiffResult`: per-pair change
  classification, the first divergence point, and aggregate deltas (Δtokens, Δcost, Δlatency,
  Δtool-calls). This is the data the viewer and CI mode both render/consume.

## Key Insights
- Diff is the single source of truth consumed by BOTH the HTML viewer (P4) and CI mode (P6) — design
  it as a plain serializable structure (dataclass → dict) so P6 can threshold on it and P4 can render
  it without re-deriving anything (DRY).
- "First divergence point" = index of first pair that is not MATCH. It's the headline UX element
  ("they agreed up to step N, then split").
- Deltas are B-minus-A by convention (B is the "new"/candidate run, A is baseline/golden). State this
  once; every label downstream follows it.

## Requirements
**Functional**
- `compute_diff(pairs: list[AlignedPair]) -> DiffResult`.
- Per-pair status reuses `Op` from P2; additionally compute a content-level changed/same flag for
  SUBSTITUTE pairs (so viewer can highlight intra-step text changes — optional inline token diff).
- `DiffResult` fields: `pairs`, `first_divergence_index|None`, `totals_a`, `totals_b`, `deltas`
  (tokens_in/out, total_tokens, cost, latency_ms, tool_calls), `summary_counts` (n match/sub/ins/del).
- `deltas` computed as B − A; tool_calls = count of steps with non-null `tool_name` per side.
- Graceful zero-handling: if a metric is all-zero (e.g., cost not tracked), delta = 0, flag
  `available=False` so viewer can hide that stat instead of showing misleading "0".

**Non-functional**
- Pure function, deterministic, JSON-serializable output (`to_dict()`), no I/O.

## Architecture
```
list[AlignedPair] ──> diff.py: compute_diff ──> DiffResult
                                                  ├── first_divergence_index
                                                  ├── deltas {Δtokens, Δcost, Δlatency, Δtools}
                                                  ├── totals_a / totals_b
                                                  └── pairs[] (status + optional inline change)
DiffResult.to_dict() ──> consumed by render (P4) + ci check (P6)
```
- `diff.py` — `DiffResult`, `Deltas`, `Totals` dataclasses + `compute_diff` + `to_dict` (≤180 lines).
- Optional helper `inline_text_diff(a, b)` (stdlib `difflib`) for SUBSTITUTE pairs — KISS, no new dep.

## Data Flow
Enters: `list[AlignedPair]` from P2. Transforms: per-pair classify → scan for first non-MATCH →
sum per-side totals → subtract. Exits: `DiffResult` (and `.to_dict()` for serialization).

## Related Code Files
**Create**
- `agentdiff/diff.py` — `Totals`, `Deltas`, `DiffResult`, `compute_diff`, `to_dict`, `inline_text_diff`.
- `tests/test_diff.py` — divergence index, delta arithmetic (B−A), zero/unavailable handling,
  tool-call counting, summary counts.

**Modify** — none (consumes P2 output; no dep changes).
**Delete** — none.

## Implementation Steps
1. Define `Totals` (sum of metrics for one trace) and `Deltas` (B−A per metric + `available` flags).
2. Implement `_sum_totals(steps) -> Totals`; tool_calls = `sum(1 for s in steps if s.tool_name)`.
3. Implement `compute_diff`: derive `totals_a/totals_b` from pairs' non-null sides, compute `deltas`,
   scan pairs for `first_divergence_index` (first op != MATCH), tally `summary_counts`.
4. For SUBSTITUTE pairs, attach `inline_text_diff` opcodes (difflib `SequenceMatcher`) for viewer.
5. Implement `to_dict()` producing a stable, JSON-safe shape (used by P4 template + P6 thresholds).
6. Mark a metric `available=False` when both sides sum to 0 for that metric.
7. Tests cover: identical → divergence None, all deltas 0; inserted step → divergence at insert index,
   positive token delta; cost-absent traces → cost `available=False`.
8. `ruff` + `pytest` green.

## Todo List
- [ ] Totals / Deltas / DiffResult dataclasses
- [ ] _sum_totals + tool-call counting
- [ ] compute_diff: deltas (B−A) + first_divergence_index + summary_counts
- [ ] inline_text_diff for SUBSTITUTE pairs (difflib)
- [ ] to_dict() JSON-safe serialization
- [ ] available=False for all-zero metrics
- [ ] tests: identical / insert / cost-absent / tool counts
- [ ] ruff + pytest green

## Success Criteria
- Identical traces → `first_divergence_index is None`, every delta 0.
- B inserts a step → divergence index = insert position; `total_tokens` delta = inserted step's tokens.
- Cost not tracked on either side → `deltas.cost.available is False` (viewer hides it).
- `to_dict()` round-trips through `json.dumps` without error.

## Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| B−A vs A−B sign confusion across phases | Med | Med | Document convention in module docstring + test asserts sign explicitly |
| Misleading 0 when metric untracked | Med | Med | `available` flag; viewer + CI both honor it |
| Divergence index off-by-one vs aligned vs raw index | Med | Med | Index into the aligned pair list (not raw step index); test pins it |

## Backwards Compatibility / Rollback
- `to_dict()` shape is the contract for P4/P6. Treat as versioned; additive changes only.
- Rollback: pure module, no side effects — safe to revert independently.

## Security Considerations
- None new; pure computation over already-validated data.

## Next Steps
- Unblocks P4 (render `DiffResult`) and P6 (threshold on `deltas`/`summary_counts`).

## Open Questions
- Should inline token-level diff ship in MVP or be P4-deferred if viewer time is tight? (Lean: compute
  here cheaply, let P4 decide to render or not.)
- Define "tool_calls" — count tool steps, or count distinct tools? (Lean: count tool-invoking steps.)
