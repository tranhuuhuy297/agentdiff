# Changelog

All notable changes to this project are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/); versioning is [SemVer](https://semver.org/).

## [0.1.0] — 2026-06-17

Initial release.

### Added
- `agentdiff diff A B` — align two agent run trajectories and render a
  self-contained HTML report (two columns, color-coded ops, first-divergence
  marker, Δtokens/Δcost/Δlatency/Δtool-calls banner) or a `--terminal` diff.
- Needleman–Wunsch step alignment scored by per-step similarity; offline lexical
  scorer (rapidfuzz) by default, opt-in semantic scorer via the `[semantic]` extra.
- Input adapters: JSONL (native schema), OpenTelemetry GenAI (OTLP/JSON spans),
  and Langfuse trace exports, with format auto-detection.
- `agentdiff check NEW --golden GOLDEN` — golden-trace regression gate for CI,
  with structural + cost + token thresholds (CLI flags or `agentdiff.toml`) and
  exit codes 0 pass / 1 drift / 2 error.
- `agentdiff golden NEW --out FILE` — save a run as a golden reference.

### Public contracts (SemVer-stable from here)
- The JSONL `Step` schema, the CLI flags, the `DiffResult` dict, and the CI
  `Verdict` JSON shape. Additive-only changes within `0.x` minor releases.
