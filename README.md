# agentdiff

**git diff, but for AI agent runs.** Align two agent run trajectories step-by-step,
mark where they diverge, and report the token / cost / latency delta — as a
self-contained HTML report or a colored terminal diff.

Runs **fully local**: no account, no upload, no API key. The default similarity
path is offline (rapidfuzz); embedding-based alignment is an opt-in extra.

> Why it exists: AgentEvals only *scores* trajectories; LangSmith has a side-by-side
> view but it's a closed SaaS. agentdiff is the open-source, local, `git diff`-style
> tool for the same job — plus a CI mode that gates runs against a golden trace.

## Install

```bash
pip install agentdiff
# optional embedding-based alignment:
pip install "agentdiff[semantic]"
```

## Quickstart

```bash
agentdiff diff examples/trace-a.jsonl examples/trace-b.jsonl
# → writes agentdiff-report.html and opens it

agentdiff diff examples/trace-a.jsonl examples/trace-b.jsonl --terminal   # colored CLI diff
```

The HTML report shows two aligned columns (A = baseline, B = candidate),
color-coded match / changed / only-in-A / only-in-B, the first divergence point,
and a banner with Δtokens, Δcost, Δlatency, Δtool-calls. It opens from `file://`
with **zero external requests**.

## Input formats

| Format | Detect | Notes |
|--------|--------|-------|
| **JSONL** | `.jsonl` / `.ndjson` | One step object per line — the native schema (below). |
| **OpenTelemetry GenAI** | `.json` with `resourceSpans` | OTLP/JSON span export; `gen_ai.*` attributes. |
| **Langfuse** | `.json` with `observations` | Langfuse trace export; observations flattened to steps. |

Override detection with `--format jsonl|otel|langfuse`.

### JSONL step schema

```json
{"step": 0, "role": "assistant", "content": "...", "tool_name": "search_web",
 "tool_args": {"q": "..."}, "tokens_in": 40, "tokens_out": 22, "cost": 0.0009, "latency_ms": 480}
```

Only `step` and `role` matter; everything else defaults. Missing numerics → `0`
(and surface as "untracked", not a misleading zero, in the diff).

## Golden-trace regression in CI

Save a known-good run, then fail CI when a new run drifts:

```bash
agentdiff golden examples/trace-a.jsonl --out golden.jsonl
agentdiff check new-run.jsonl --golden golden.jsonl \
  --max-cost-delta-pct 10 --max-token-delta-pct 20
```

Exit codes: **0** pass · **1** drift (policy breached) · **2** load/usage error.
Thresholds also load from `agentdiff.toml` / `.agentdiff.toml` (CLI flags win).
See `examples/agentdiff.toml` and `.github/workflows/agentdiff-check-example.yml`.

## How it works

```
load (adapter) → align (Needleman–Wunsch, similarity-scored) → diff (B−A deltas) → render / gate
```

Alignment uses global sequence alignment so reordered/inserted/deleted steps line
up the way `git diff` would. Default scoring is lexical (offline); `--semantic`
swaps in embedding cosine similarity (requires the `[semantic]` extra).

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

## License

MIT
