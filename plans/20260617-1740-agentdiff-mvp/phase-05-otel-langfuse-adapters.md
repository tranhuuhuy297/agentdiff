# Phase 05 — OpenTelemetry GenAI + Langfuse Adapters

## Context Links
- Overview: [plan.md](plan.md)
- Prev: [phase-04-html-viewer-cli.md](phase-04-html-viewer-cli.md)
- Next: [phase-06-golden-trace-ci-mode.md](phase-06-golden-trace-ci-mode.md)

## Overview
- **Priority:** P2
- **Status:** pending
- **Description:** Add two more input adapters so real-world exports drop in: OpenTelemetry GenAI
  spans (emerging standard) and Langfuse trace exports. Both normalize to the same `Trace` model.
- **Parallelizable:** depends only on P1's data model + `base.py`. Touches only `adapters/` — can be
  built alongside P2/P3 with no file conflict.

## Key Insights
- OTel GenAI semantic conventions define span attributes like `gen_ai.system`, `gen_ai.usage.input_tokens`,
  `gen_ai.usage.output_tokens`, and tool spans — map these onto `Step`. Accept OTLP JSON export
  (the exported spans file), not a live collector (KISS: file in, like every other adapter).
- Langfuse exports nest observations (generations/spans) under a trace; flatten ordered observations
  into steps, mapping usage + cost fields Langfuse already computes.
- One ordering rule across both: sort spans/observations by start timestamp → assign `step` index. This
  is the only tricky transform; everything else is field mapping reusing `normalize_step` (DRY).

## Requirements
**Functional**
- `load_otel(path) -> Trace`: parse OTLP/JSON spans; filter GenAI spans; map attrs→Step fields;
  order by start time; latency from span duration.
- `load_langfuse(path) -> Trace`: parse Langfuse trace JSON export; flatten observations→steps;
  map `usage.input/output`, `calculatedTotalCost`, tool calls.
- CLI adapter dispatch extended: detect by extension/shape (`--format otel|langfuse|jsonl` override).
- Unknown/partial fields default per `base.normalize_step`; missing cost/tokens → 0 (P3 marks unavailable).

**Non-functional**
- Pure parse, no live network/collector. No new heavy deps — prefer stdlib `json`; only add a light
  dep if a format genuinely needs it (avoid pulling full `opentelemetry-sdk`).

## Architecture
```
otlp-spans.json --(adapters/otel.py: load_otel)--------┐
langfuse-trace.json --(adapters/langfuse.py: load_langfuse)─┤─> normalize_step (base.py) ─> Trace
                                                        ┘
cli.py: _detect_format(path)/--format ─> dispatch to {jsonl|otel|langfuse} loader
```
- `adapters/otel.py` — span extraction + GenAI attr mapping (≤180 lines).
- `adapters/langfuse.py` — observation flattening + field mapping (≤160 lines).
- `cli.py` — extend dispatch + `--format` override (small edit).

## Data Flow
Enters: an OTLP-JSON or Langfuse-JSON export file. Transforms: parse → select relevant spans/obs →
sort by timestamp → field-map via `normalize_step`. Exits: a `Trace` identical in shape to JSONL's.

## Related Code Files
**Create**
- `agentdiff/adapters/otel.py` — `load_otel`.
- `agentdiff/adapters/langfuse.py` — `load_langfuse`.
- `examples/trace-otel.json`, `examples/trace-langfuse.json` — small real-shaped fixtures.
- `tests/test_otel_adapter.py`, `tests/test_langfuse_adapter.py` — mapping correctness, ordering,
  missing-field defaults, cross-adapter equivalence (same logical run → equivalent Trace).

**Modify**
- `agentdiff/cli.py` — add `_detect_format`, `--format` flag, dispatch table.
- `agentdiff/adapters/__init__.py` — export new loaders + a `get_loader(name)` registry (DRY dispatch).
- `README.md` — document supported input formats.

**Delete** — none.

## Implementation Steps
1. Capture realistic minimal fixtures: an OTLP/JSON export with 2–3 GenAI spans incl. a tool span; a
   Langfuse trace export with generations + a tool observation. (Pull shapes from public docs/samples.)
2. Implement `load_otel`: walk `resourceSpans→scopeSpans→spans`; keep spans with `gen_ai.*` attrs;
   map system/model/tokens/tool name+args; latency = (endTimeUnixNano−startTimeUnixNano)/1e6; sort.
3. Implement `load_langfuse`: read trace, iterate observations sorted by `startTime`; map type→role,
   usage→tokens, `calculatedTotalCost`→cost, tool fields→tool_name/args.
4. Add `adapters/__init__.get_loader(format)` registry; `cli._detect_format` by extension+content sniff
   (`.jsonl`→jsonl; `.json` with `resourceSpans`→otel; with Langfuse keys→langfuse).
5. Tests: field mapping, timestamp ordering, missing usage→0, and a parity test that an OTel fixture and
   an equivalent JSONL fixture align with zero divergence.
6. `ruff` + `pytest` green.

## Todo List
- [ ] OTel + Langfuse fixtures in examples/
- [ ] load_otel (GenAI attr mapping + duration latency + ordering)
- [ ] load_langfuse (observation flattening + usage/cost mapping)
- [ ] get_loader registry + cli _detect_format + --format flag
- [ ] tests: mapping / ordering / defaults / cross-adapter parity
- [ ] README formats section
- [ ] ruff + pytest green

## Success Criteria
- `agentdiff run.otlp.json other.otlp.json` produces a diff without format flags (auto-detected).
- `--format langfuse` forces the Langfuse loader.
- An OTel export and a logically-equivalent JSONL trace align with `first_divergence_index is None`.
- Missing token/cost fields surface as `available=False` downstream, not fake zeros.

## Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| OTel GenAI conventions still evolving / version drift | High | Med | Map a documented attribute subset; tolerate missing attrs; pin tested convention version in docstring |
| Format auto-detection misfires (.json ambiguous) | Med | Med | Content sniff for signature keys; always allow explicit `--format` override |
| Pulling heavy otel SDK bloats install | Low | Med | Parse OTLP/JSON with stdlib json only; no SDK dependency |
| Langfuse export schema changes across versions | Med | Med | Defensive `.get()` mapping; fixture pins a known schema; document tested version |

## Backwards Compatibility / Rollback
- Adapters are additive; JSONL path unchanged. `get_loader` registry isolates dispatch growth.
- Rollback: remove a loader from the registry — JSONL + others unaffected.

## Security Considerations
- Same untrusted-input rules as P1: stdlib json only, size guard, no eval. Content still escaped at
  render time (P4) regardless of source adapter.

## Next Steps
- Broadens inputs; orthogonal to P6. P7 packages all adapters + documents the format matrix.

## Open Questions
- Pin which OTel GenAI convention revision as the supported baseline (note in docstring + README).
- Support OTLP protobuf as well as JSON, or JSON-only for MVP? (Lean: JSON-only; protobuf later.)
