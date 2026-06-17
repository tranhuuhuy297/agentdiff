# Phase 02 — Step Alignment Algorithm (Needleman–Wunsch)

## Context Links
- Overview: [plan.md](plan.md)
- Prev: [phase-01-scaffold-datamodel-jsonl-adapter.md](phase-01-scaffold-datamodel-jsonl-adapter.md)
- Next: [phase-03-diff-delta-computation.md](phase-03-diff-delta-computation.md)

## Overview
- **Priority:** P1 (the core "smart" part; the differentiator)
- **Status:** pending
- **Description:** Align two `list[Step]` so reordered/inserted/deleted steps line up, using
  global sequence alignment (Needleman–Wunsch) scored by per-step similarity. Output is a list of
  aligned pairs: `(step_a|None, step_b|None, op)` where op ∈ match/substitute/insert/delete.

## Key Insights
- Why NW (global) not LCS or greedy: agent runs share a long common prefix then diverge; NW with a
  similarity-weighted scoring matrix yields the diff-style alignment users expect from `git diff`.
- Similarity must work **offline by default**. Default scorer = token/string similarity via
  `rapidfuzz` (fast C++); `--semantic` swaps in `fastembed` cosine similarity. Pluggable scorer fn
  keeps NW core pure and dependency-free (DRY/KISS).
- Similarity should weight `tool_name` heavily (exact tool match is a strong signal) blended with
  content similarity — a tool-call step and a plain-text step should rarely align.

## Requirements
**Functional**
- `align(a: list[Step], b: list[Step], scorer, gap_penalty) -> list[AlignedPair]`.
- Scorer: `(Step, Step) -> float` in [0,1]. Two built-ins: `lexical_similarity` (default),
  `semantic_similarity` (optional, requires `semantic` extra; raises clear error if missing).
- NW: build score matrix, traceback → ordered ops preserving sequence order.
- Configurable `gap_penalty` and `match_threshold` (below threshold a same-position pair is
  "substitute" not "match").

**Non-functional**
- Pure function, no I/O, no network in the lexical path. Deterministic.
- O(n·m) time/space acceptable for MVP (traces are tens–hundreds of steps); document the bound.

## Architecture
```
list[Step]_a , list[Step]_b
        │
        ▼   scorer(step_a, step_b) -> [0,1]
  align.py: needleman_wunsch(score_fn, gap)
        │  (matrix + traceback)
        ▼
  list[AlignedPair(a, b, op)]   op: MATCH|SUBSTITUTE|INSERT_B|DELETE_A
```
- `align.py` — NW core + `AlignedPair`, `Op` enum. Pure.
- `similarity.py` — `lexical_similarity` (rapidfuzz) + `semantic_similarity` (fastembed, lazy import)
  + `blended_score` combining content + tool_name weight. Embedding model lazy-loaded & cached.

## Data Flow
Enters: two `list[Step]`. Transforms: pairwise similarity → DP matrix → traceback. Exits: ordered
`list[AlignedPair]`. No metrics computed here (that's P3) — alignment only decides *which steps pair*.

## Related Code Files
**Create**
- `agentdiff/align.py` — `Op` enum, `AlignedPair` dataclass, `needleman_wunsch(...)`, `align(...)` (≤170 lines).
- `agentdiff/similarity.py` — `lexical_similarity`, `semantic_similarity`, `blended_score`, scorer factory.
- `tests/test_align.py` — identical traces (all MATCH), one inserted step, one reordered, one deleted.
- `tests/test_similarity.py` — lexical determinism; tool-name weighting; semantic skipped if extra absent.

**Modify**
- `pyproject.toml` — add `rapidfuzz` to core deps (small, pure-wheel, no API key).
- `examples/` — extend sample traces to exercise insert + reorder if needed.

**Delete** — none.

## Implementation Steps
1. Define `Op` (enum) and `AlignedPair(a: Step|None, b: Step|None, op: Op, score: float)`.
2. Implement `lexical_similarity(s1, s2)`: rapidfuzz ratio on `content`; combine with exact
   `tool_name` match bonus via `blended_score(content_sim, tool_match, w=...)`.
3. Implement `needleman_wunsch`: init matrix with gap penalties, fill using `match = score - 0.5`
   style affine-free scoring (document scoring scheme), traceback to ops.
4. Implement `align()`: pick scorer (lexical default; semantic if requested), run NW, classify each
   diagonal move as MATCH if `score >= match_threshold` else SUBSTITUTE.
5. Implement `semantic_similarity`: lazy `from fastembed import TextEmbedding`; cache model; cosine of
   content embeddings; raise `RuntimeError` with install hint if `fastembed` not installed.
6. Tests: identical → all MATCH; insert one step in B → exactly one INSERT_B, rest MATCH; reorder →
   alignment recovers pairs not naive position match; delete → one DELETE_A.
7. `ruff` + `pytest` green.

## Todo List
- [ ] Op enum + AlignedPair
- [ ] similarity.py lexical + blended (tool weighting)
- [ ] needleman_wunsch core + traceback
- [ ] align() with threshold-based MATCH/SUBSTITUTE
- [ ] semantic_similarity (lazy fastembed, clear error if absent)
- [ ] tests: identical / insert / reorder / delete
- [ ] ruff + pytest green

## Success Criteria
- Identical traces → every pair MATCH, zero gaps.
- B has one extra step → exactly one INSERT_B; all real pairs still MATCH.
- Two swapped steps → algorithm pairs them correctly (not by raw index).
- Runs with no network and no API key on the default path.
- `--semantic` path works when extra installed; gives actionable error when not.

## Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| NW scoring tuned wrong → bad alignments | Med | High | Expose `gap_penalty`/`match_threshold`; lock behavior with the 4 golden alignment tests |
| O(n·m) memory on huge traces | Low | Med | Document bound; add step-count guard with warning; banding is a documented future opt (YAGNI now) |
| fastembed model download fails offline | Med | Low | Lexical is default; semantic clearly optional; error names the `[semantic]` extra |
| Over-weighting tool_name hides content drift | Med | Med | Blend, don't replace; weight configurable; tests assert both signals contribute |

## Backwards Compatibility / Rollback
- New module, additive. Public surface = `align()`. Keep its signature stable for P3/P4/P6 consumers.
- Rollback: P3 only depends on `AlignedPair` shape — revert align.py without touching downstream contract.

## Security Considerations
- Embedding path may download a model on first use — only when user opts into `--semantic`. Document
  the network access explicitly so "local-first" promise is honest.

## Next Steps
- Unblocks P3: delta computation walks `list[AlignedPair]` to find first divergence + sum metric deltas.

## Open Questions
- Exact scoring scheme + default `match_threshold` (calibrate against example traces in P3 review).
- Which fastembed model default (size vs quality) — pick smallest viable; revisit post-MVP.
