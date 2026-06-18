# Phase 04 — HTML Viewer + CLI Wiring (MVP demo cut)

## Context Links
- Overview: [plan.md](plan.md)
- Prev: [phase-03-diff-delta-computation.md](phase-03-diff-delta-computation.md)
- Next: [phase-05-otel-langfuse-adapters.md](phase-05-otel-langfuse-adapters.md)

## Overview
- **Priority:** P1 (this is the shippable MVP — `agentdiff a.jsonl b.jsonl` → report)
- **Status:** done
- **Description:** Render a `DiffResult` into a single self-contained HTML file (two aligned columns,
  color-coded, divergence marker, delta banner) and wire the `agentdiff` CLI to load → align → diff →
  render/open. Also a `--terminal` colored text diff path.

## Key Insights
- "Self-contained" = one HTML file, inline CSS + inline JS, no CDN, no server. Jinja2 renders the diff
  data as an embedded `<script>` JSON blob; vanilla JS builds the two columns. Opens via `file://`.
  This is the local-first promise made concrete.
- The CLI is the product's whole UX surface — match `git diff` ergonomics: positional `a b`, sensible
  defaults (writes report to a temp/`agentdiff-report.html`, opens browser unless `--no-open`).
- Terminal diff (rich) is the fast-feedback path and the CI-friendly output; HTML is the deep-dive.

## Requirements
**Functional**
- `agentdiff A B [--out FILE] [--no-open] [--terminal] [--semantic] [--gap N] [--threshold F]`.
- Auto-detect adapter by extension/content (`.jsonl`→jsonl; OTel/Langfuse arrive in P5) → `Trace`.
- Pipeline: load A, load B → `align` → `compute_diff` → render.
- HTML: header banner (Δtokens, Δcost, Δlatency, Δtool-calls, with arrows + color; hide unavailable);
  two columns A|B; rows color-coded same/changed/only-A/only-B; first-divergence row anchored + marked;
  click a row → expand full content / tool_args.
- Terminal mode: rich-rendered side-by-side or unified colored diff + the delta summary line.

**Non-functional**
- Rendered HTML must open offline with no external requests (verify: no `http(s)://` asset refs).
- Render is pure (`DiffResult` → html string); file write + browser open isolated in cli.

## Architecture
```
cli.py (typer app)
  load_jsonl(A) ─┐
  load_jsonl(B) ─┴─> align() ─> compute_diff() ─> render_html(DiffResult) ─> write file ─> webbrowser.open
                                              └──> render_terminal(DiffResult) (rich)  [--terminal]
render/__init__.py: render_html, render_terminal
render/viewer.html.j2: Jinja2 template, inline <style> + <script>, {{ diff_json }} injected
```
- `render/viewer.html.j2` — the single-file template (HTML/CSS/JS; JS reads embedded JSON).
- `render/__init__.py` — `render_html(diff, meta) -> str` (jinja2), `render_terminal(diff)` (rich).
- `cli.py` — typer `app`; one command `diff` as default; adapter dispatch; orchestration only.

## Data Flow
Enters: two file paths + flags. Transforms: paths→Traces→AlignedPairs→DiffResult→html/text string.
Exits: an HTML file on disk (opened in browser) or colored text on stdout. I/O lives only here.

## Related Code Files
**Create**
- `agentdiff/cli.py` — typer app, `diff` command, adapter dispatch, write+open (≤150 lines).
- `agentdiff/render/__init__.py` — `render_html`, `render_terminal`.
- `agentdiff/render/viewer.html.j2` — self-contained template (not counted by 200-line rule; it's a template/markup asset, but keep JS modular & readable).
- `tests/test_render.py` — `render_html` returns string containing banner deltas + no `http://` refs;
  `render_terminal` produces output without raising.
- `tests/test_cli.py` — typer `CliRunner`: `agentdiff A B --no-open --out tmp` writes a file; exit 0;
  bad path → exit !=0 with message.
- `examples/demo.gif` (placeholder note; actual GIF produced at release in P7).

**Modify**
- `pyproject.toml` — confirm `jinja2`, `rich` (rich ships with typer extras) in core deps; package the
  `.j2` template via `[tool.hatch.build]` include / package-data so it ships in the wheel.
- `README.md` — quickstart: install + `agentdiff a.jsonl b.jsonl`.

**Delete** — none.

## Implementation Steps
1. Add `jinja2` dep; ensure template packaged (hatch `include` / `force-include`). Load template via
   `importlib.resources` (works installed, not just from source tree).
2. Build `viewer.html.j2`: inline CSS (color tokens for same/changed/only-A/only-B), a banner section,
   a two-column grid, and `<script>` that parses embedded `{{ diff_json }}` and builds rows; anchor +
   scroll to `first_divergence_index`; row click toggles full content/tool_args.
3. Implement `render_html(diff, meta)`: `diff.to_dict()` → `json.dumps` → jinja2 render → str.
4. Implement `render_terminal(diff)` with rich: summary line + per-row colored side-by-side; respect
   `available=False` (hide that stat).
5. Implement `cli.py`: typer app; `diff(a, b, out, no_open, terminal, semantic, gap, threshold)`;
   dispatch adapter by extension; run pipeline; if `--terminal` print, else write `out`
   (default `agentdiff-report.html`) and `webbrowser.open` unless `--no-open`.
6. Verify generated HTML has zero external network references (grep the rendered output in test).
7. Manual smoke: run on `examples/trace-a.jsonl examples/trace-b.jsonl`, eyeball the report.
8. `ruff` + `pytest` green.

## Todo List
- [x] Package + load `.j2` via importlib.resources
- [x] viewer.html.j2: banner + 2 columns + color codes + divergence anchor + row expand
- [x] render_html (jinja2) — embedded JSON, no external refs
- [x] render_terminal (rich) honoring availability
- [x] cli.py: typer app, adapter dispatch, write+open, flags
- [x] tests: render (no http refs, banner present) + cli (CliRunner exit codes)
- [x] README quickstart
- [x] ruff + pytest green

## Success Criteria
- `agentdiff examples/trace-a.jsonl examples/trace-b.jsonl` opens an HTML report showing two columns,
  divergence marked, delta banner populated.
- Generated HTML opens from `file://` with network disabled (no failed asset loads).
- `--terminal` prints a readable colored diff + delta summary.
- `--out path --no-open` writes the file and does not launch a browser; exit 0.
- Bad input path → non-zero exit + clear message.

## Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Template not packaged → import fails when installed | Med | High | Load via `importlib.resources`; cli test runs against installed package layout |
| Accidental CDN/font fetch breaks offline promise | Med | High | Test greps rendered HTML for `http://`/`https://`; fail build if found |
| Large traces → huge HTML / slow JS render | Low | Med | Embed JSON + client render (no per-row server HTML); virtualize only if needed (YAGNI) |
| webbrowser.open fails on headless/CI | Med | Low | `--no-open` default-on when no DISPLAY / `CI` env; always still write file |

## Backwards Compatibility / Rollback
- CLI flags are public surface → keep stable post-release; additive flags only.
- Rollback: render/cli are leaf modules; revert without touching align/diff contracts.

## Security Considerations
- Embedding untrusted trace content into HTML → **escape on render** (JSON-encode into `<script>` and
  let JS set `textContent`, never `innerHTML` of raw content) to prevent stored-XSS via malicious trace.
- `webbrowser.open` only on a local file path we wrote; never open arbitrary URLs from input.

## Next Steps
- MVP is demo-able here. P5 adds adapters (more inputs), P6 adds CI mode (reuses pipeline minus render).

## Open Questions
- Vanilla JS vs preact for the viewer JS — lean vanilla for zero build step (KISS); revisit if the row
  interactions grow.
- Default output location: cwd `agentdiff-report.html` vs temp dir? (Lean: cwd, predictable for users.)
