# Phase 07 — Tests, Packaging, and Release

## Context Links
- Overview: [plan.md](plan.md)
- Prev: [phase-06-golden-trace-ci-mode.md](phase-06-golden-trace-ci-mode.md)

## Overview
- **Priority:** P2 (release gate over all prior phases)
- **Status:** pending
- **Description:** Consolidate the test matrix, finalize packaging (wheel includes the HTML template),
  set up project CI, polish README + demo GIF, and publish `0.1.0` to PyPI. Definition of "released".

## Key Insights
- Each prior phase shipped its own focused tests; P7 adds the *integration/end-to-end* layer and the
  *release plumbing* — it does not re-test units. The end-to-end test is the real proof: file in →
  HTML/verdict out.
- The single biggest packaging risk across the project is the Jinja template + viewer JS not shipping
  in the wheel. P7 explicitly verifies install-from-wheel in a clean environment.
- OSS launch quality = a README that shows the diff in 10 seconds (GIF) + a one-command quickstart +
  honest "local-first, no account" framing. That framing is the differentiator; make it loud.

## Requirements
**Functional**
- End-to-end tests covering: jsonl→diff→html; otel→diff; langfuse→diff; `check` pass/fail exit codes.
- `pytest` with coverage; target ≥80% on core (`models`, `align`, `diff`, `ci`); render/cli exercised
  via CliRunner + string assertions.
- Build wheel + sdist; install wheel in a fresh venv; run `agentdiff` against examples → works (proves
  template + package-data shipped).
- GitHub Actions: lint (ruff) + test (matrix py3.11–3.13) + build; optional publish-on-tag to PyPI
  (trusted publishing / OIDC, no stored token).

**Non-functional**
- Reproducible build; pinned dev deps; semantic version `0.1.0`.
- README, LICENSE (MIT), CHANGELOG, format-support matrix, contributing note.

## Architecture
```
tests/test_end_to_end.py ── runs full pipeline on examples/ fixtures
.github/workflows/ci.yml ── ruff + pytest matrix (py3.11–3.13) + build wheel
.github/workflows/release.yml ── on tag v*: build + publish (OIDC trusted publishing)
pyproject.toml ── final metadata, classifiers, urls, package-data (viewer.html.j2)
README.md ── quickstart + demo.gif + formats + CI usage + local-first framing
```

## Related Code Files
**Create**
- `tests/test_end_to_end.py` — full-pipeline assertions per input format + `check` exit codes.
- `tests/conftest.py` — shared fixtures (paths to example traces, tmp output dirs).
- `.github/workflows/ci.yml` — lint+test+build matrix.
- `.github/workflows/release.yml` — tag-triggered PyPI publish via OIDC.
- `CHANGELOG.md` — `0.1.0` initial entry.
- `CONTRIBUTING.md` — dev setup, run tests, lint, adding an adapter.
- `examples/demo.gif` — recorded terminal+browser demo (replace P4 placeholder).

**Modify**
- `pyproject.toml` — classifiers, project URLs, `[tool.hatch.build.targets.wheel]` include template,
  `[tool.pytest.ini_options]`, coverage config, finalize version `0.1.0`.
- `README.md` — finalize: badges, quickstart, GIF, formats matrix, golden-trace CI section.

**Delete** — none.

## Implementation Steps
1. Add `conftest.py` fixtures + `test_end_to_end.py`: for each example format, load→align→diff→
   render_html (assert banner + no external refs) and run `check` (assert exit codes).
2. Configure coverage in pyproject; run `pytest --cov`; raise core coverage to ≥80% (add targeted unit
   tests where gaps remain).
3. Finalize `pyproject.toml`: metadata, classifiers (License MIT, Python versions), URLs (repo/issues),
   ensure `viewer.html.j2` included in wheel build target.
4. Build: `python -m build`; create fresh venv; `pip install dist/*.whl`; run
   `agentdiff examples/trace-a.jsonl examples/trace-b.jsonl --no-open --out /tmp/r.html` → assert file
   written (proves template shipped). Add this as a CI job step.
5. Author `ci.yml` (ruff + pytest on py3.11–3.13 + build) and `release.yml` (tag `v*` → build → publish
   via PyPI trusted publishing/OIDC).
6. Record `demo.gif` (terminal diff + HTML report); embed in README; write quickstart + formats matrix
   + golden-trace CI section + local-first/no-account framing.
7. Write `CHANGELOG.md` `0.1.0`; tag `v0.1.0`; verify release workflow publishes.
8. Final `ruff` + `pytest` green across the matrix.

## Todo List
- [ ] conftest.py shared fixtures
- [ ] test_end_to_end.py (all formats + check exit codes)
- [ ] coverage config + ≥80% core coverage
- [ ] pyproject finalize (classifiers, URLs, wheel include template)
- [ ] build + clean-venv install smoke (template ships)
- [ ] ci.yml (ruff + pytest matrix + build)
- [ ] release.yml (OIDC trusted publishing on tag)
- [ ] demo.gif + README finalize + CHANGELOG
- [ ] tag v0.1.0 + publish verified

## Success Criteria
- `pytest` green on py3.11–3.13; core coverage ≥80%.
- Wheel installs in a clean venv and `agentdiff` runs end-to-end (template + data shipped).
- CI workflow passes on a fresh clone; tagging `v0.1.0` publishes to PyPI via OIDC (no stored secret).
- README renders quickstart + GIF; a new user diffs two traces within ~1 minute of `pip install`.

## Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Template/data not in wheel → broken install | Med | High | Clean-venv install smoke test in CI gates release |
| fastembed `[semantic]` extra breaks on some platforms | Med | Med | Keep it an optional extra; core install stays lean; CI tests core path without it |
| PyPI publish misconfig leaks token | Low | High | Use OIDC trusted publishing — no stored token at all |
| Coverage gate too strict slows release | Low | Low | 80% on core modules only; render/cli via CliRunner, not line-coverage-maxed |

## Backwards Compatibility / Rollback
- First public release (`0.1.0`); establishes the public contracts (Step schema, CLI flags, Verdict
  JSON, DiffResult dict). Post-release: SemVer, additive-only within minor versions.
- Rollback: yank a bad PyPI release; CI build artifacts retained; revert tag.

## Security Considerations
- Supply chain: pin/lock dev deps; OIDC publishing (no long-lived PyPI token). Re-confirm no external
  network refs in shipped HTML template (carry P4's grep test into the e2e suite).

## Next Steps (post-MVP, out of scope here)
- OTLP protobuf input; suite-mode golden directories; viewer inline token-diff polish; more adapters
  (LangSmith export, Arize/Phoenix). Each is additive on the locked `Trace`/`DiffResult` contracts.

## Open Questions
- PyPI project name availability (`agentdiff`) — verify before tagging; fallback name if taken.
- Minimum supported Python: **decided 3.11** in P1 (so P6 uses stdlib `tomllib`, no `tomli` backport).
  Revisit only if a 3.10 user need surfaces — then add `tomli; python_version<"3.11"` and adjust CI
  matrix lower bound. CI matrix here is therefore py3.11–3.13.
