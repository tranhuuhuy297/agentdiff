---
title: "agentdiff MVP — git diff for AI agent runs"
description: "CLI + HTML viewer that aligns two agent run trajectories, marks divergence, and reports token/cost/latency delta."
status: done
priority: P2
effort: ~30h (7 phases)
branch: main
tags: [open-source, cli, ai-agents, diff, python]
created: 2026-06-17
---

# agentdiff — Implementation Plan

**One line:** "git diff, but for AI agent runs." Align two agent trajectories step-by-step,
highlight divergence, summarize token/cost/latency delta. Runs fully local, format-agnostic.

## Differentiation (preserve in every phase)
Open source · no account/upload · local-first · git-diff ergonomics (`agentdiff a.jsonl b.jsonl`)
· CI golden-trace regression. Niche verified open vs AgentEvals (scoring only) & LangSmith (closed SaaS).

## Tooling Decisions (justified in phase files)
- **Packaging:** `pyproject.toml` + hatchling (PEP 621, zero-config, src-less layout works).
- **CLI:** `typer` (type-hint driven, less boilerplate than click, ships rich for colored terminal diff).
- **Templating:** `jinja2` (mature, single-file render → self-contained HTML).
- **Similarity:** string/token (rapidfuzz) as DEFAULT offline path; `fastembed` optional extra for
  semantic alignment (ONNX, no torch, downloads model once). No API key ever required.
- **Tests:** `pytest`. **Lint/format:** `ruff`.

## Phases (each independently shippable)

| # | Phase | Status | Ships |
|---|-------|--------|-------|
| 1 | [Scaffold + data model + JSONL adapter](phase-01-scaffold-datamodel-jsonl-adapter.md) | done | Load + validate a trace |
| 2 | [Step alignment (Needleman–Wunsch)](phase-02-step-alignment-algorithm.md) | done | Aligned step pairs |
| 3 | [Diff + delta computation](phase-03-diff-delta-computation.md) | done | Divergence + Δ metrics |
| 4 | [HTML viewer + CLI wiring](phase-04-html-viewer-cli.md) | done | `agentdiff a b` → report |
| 5 | [OTel + Langfuse adapters](phase-05-otel-langfuse-adapters.md) | done | Drop-in exports |
| 6 | [Golden-trace CI regression mode](phase-06-golden-trace-ci-mode.md) | done | `agentdiff check` exit codes |
| 7 | [Tests + packaging + release](phase-07-tests-packaging-release.md) | done | PyPI + CI green |

## Dependency Graph
```
P1 ─┬─> P2 ─> P3 ─> P4 (MVP demo-able after P4)
    └────────────> P5 (adapters; needs P1 data model only)
P3 ─> P6 (CI mode reuses delta computation)
P1..P6 ─> P7 (tests + release gate over all)
```
- **MVP cut line:** P1–P4 deliver the demo-able tool. P5–P7 harden + extend.
- **Parallelizable:** P5 (adapters) can run alongside P2/P3 — touches only `adapters/`, no overlap.

## Key Cross-Phase Invariants
- Canonical in-memory model = `Trace(list[Step])`. Every adapter outputs this; every consumer reads it.
- Alignment is pure (no I/O); diff is pure; render is pure. I/O isolated to adapters + cli.
- Files ≤200 lines; pure functions; no network unless `--semantic` explicitly passed.

## Open Questions
See each phase's "Open Questions" section. Top-level unresolved items rolled up in P7.
