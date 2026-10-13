# Review 1 — HLB9Q Add MCP tool: body battery

**Verdict: PASS** (one Important finding reported; all coverage complete)

Review of `wi/2-add-mcp-tool-body-battery` against the merge base. The `get_body_battery` tool matches the work item: single request for the range, per-day summary plus 2-hourly series, version 0.5.0, docs and e2e test updated. All checks pass from a fresh install.

## Scope manifest

- SCOPE_ID: e4b1f1d6 (derived from the patch SHA-256 below, baseline and implementation)
- REPOSITORY_ROOT: /tmp/dev-dashboard-run/repo
- BASELINE: 626c0ff6db5bd5789b29e2d83d38cd1c7011e5c7
- IMPLEMENTATION: d2f181eebd5e055c42c82834389fdf6bfda092f2
- DIFF_SOURCE: `git diff --find-renames 626c0ff d2f181e` excluding `work/open/HLB9Q-.../*.review-*.md`
- CHANGED_PATHS: M AGENTS.md, README.md, pyproject.toml, src/my_garmin_mcp/__init__.py, garmin/dates.py, garmin/extract.py, tools/__init__.py, tests/test_e2e.py, tests/test_extract.py, tests/test_tools.py, uv.lock, work/future-improvements.md; A src/my_garmin_mcp/tools/body_battery.py, work/open/HLB9Q-.../HLB9Q-add-mcp-tool-body-battery.report.md
- PATCH_SHA256: e4b1f1d62d1095a2c8b0b2922308b70cace31d9d87f01a6eb7d642f322d94434
- No deletions or renames. The tree was clean and unchanged throughout.
- Rules: AGENTS.md (CLAUDE.md content), docs/conventions/*.

## Coverage ledger

Change set: 9 source files (5 under src/, 3 tests, plus pyproject), 244 changed lines excluding docs, lockfile and the work item folder, so every role was dispatched as a subagent.

| Role | Covered by | Status | Dispatches/retries |
|---|---|---|---|
| CCA | subagent | complete | 1/0 |
| CCB | subagent | complete | 1/0 |
| DCS | subagent | complete | 1/0 |
| CSS | subagent | complete | 1/0 |
| EHS | subagent | complete | 1/0 |
| DBS | subagent | complete | 1/0 |
| TCS | subagent | complete | 1/0 |

No role was covered inline.

## Checks

| Command | Result |
|---|---|
| `uv sync --locked` | exit 0 |
| `uv run pytest` (unit, tool and e2e MCP client tests) | exit 0, 55 passed |
| `uv run ruff check .` | exit 0, all checks passed |
| `uv run ruff format --check .` | exit 0, 48 files formatted |
| Type check | not declared by the project; none run |

No tracked file was rewritten. No database suite exists.

## Candidates

| ID | Path:line | Category | Evidence | Conf. | Disposition |
|---|---|---|---|---|---|
| CCB-1 | AGENTS.md:29 | docs order | Docs list the tool after heart rate, registration order differs. Cosmetic. | 15 | rejected (below threshold) |
| TCS-1 | src/my_garmin_mcp/garmin/extract.py:128 | untested branch | `_epoch_ms` ISO-string branch (Garmin's normal `startTimestampGMT`/`startTimestampLocal` form) is untested. Only integer timestamps appear in tests. I confirmed it works today. | 80 | reported |
| TCS-2 | extract.py:171 | untested branch | Offset falls back to 0 when a timestamp is missing; untested. | 45 | rejected |
| TCS-3 | extract.py:146 | untested branch | Descriptor guards (missing key, invalid index) untested. | 40 | rejected |
| TCS-4 | tests/test_tools.py:170 | weak assertion | 31-day boundary not asserted. | 25 | rejected |
| EHS-1 | extract.py:191 | edge case | NaN/inf/huge timestamp raises in `fromtimestamp`. I reproduced it. A JSON payload from Garmin carrying such values is not shown to be reachable, and `heart_rate_day` has the same pattern. | 55 | rejected |
| EHS-2 | extract.py:171 | edge case | Extreme ISO years or inf offset raise OverflowError. Not shown reachable. | 40 | rejected |
| EHS-3 | extract.py:144 | edge case | Non-iterable descriptor list raises TypeError. Speculative. | 25 | rejected |
| EHS-4 | extract.py:210 | edge case | Mixed-type `date` values break the sort. Speculative. | 20 | rejected |
| EHS-5 | extract.py:182 | edge case | NaN level gives non-standard JSON. Same gap as baseline. | 15 | rejected |

CCA, DCS, CSS and DBS returned no candidates. No `CHK` candidates, since all checks passed.

## Findings

### Important

#### 1. ISO-string timestamp path of `_epoch_ms` has no test

- **Path:line**: `src/my_garmin_mcp/garmin/extract.py:128`
- **Category**: test-coverage
- **Confidence**: 80
- **Problem**: Garmin returns `startTimestampGMT` and `startTimestampLocal` as ISO strings, so the ISO branch of `_epoch_ms` is the main production path for the local-time offset. Every test passes integers or omits the fields.
- **Reproduction**: Replace the `fromisoformat` branch with `return None`. The offset becomes 0, readings are bucketed in GMT, and all 55 tests still pass.
- **Fix direction**: Add a `body_battery_days` test with ISO strings, for example GMT `2026-10-01T04:00:00.0` and local `2026-10-01T06:00:00.0`, expecting local-time readings. Also cover a naive string and an unparseable string.
- **Regression test location**: `tests/test_extract.py`
