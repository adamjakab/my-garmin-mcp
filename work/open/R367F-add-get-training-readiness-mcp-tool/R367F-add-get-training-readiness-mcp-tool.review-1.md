# Review 1: R367F add get_training_readiness MCP tool

**Verdict: PASS**

Scope manifest (frozen):

- SCOPE_ID: R367F-5ff3a5e
- REPOSITORY_ROOT: /tmp/dev-dashboard-run/repo
- BASELINE (merge-base): 8263dfa78ea88316021813ccbcb77b0c778b13f6
- IMPLEMENTATION: 5ff3a5e25ccb7502e93222d8034a2a9cc11d7e07
- DIFF_SOURCE: `git diff --find-renames 8263dfa 5ff3a5e`, excluding `work/open/R367F-*/*.review-<N>.md`
- CHANGED_PATHS: AGENTS.md (M), README.md (M), pyproject.toml (M), uv.lock (M), work/future-improvements.md (M), src/my_garmin_mcp/__init__.py (M), src/my_garmin_mcp/garmin/extract.py (M), src/my_garmin_mcp/tools/__init__.py (M), src/my_garmin_mcp/tools/training_readiness.py (A), tests/test_e2e.py (M), tests/test_extract.py (M), tests/test_tools.py (M), work/open/R367F-.../R367F-....report.md (A). No deletions or renames.
- PATCH_SHA256 (src+tests+docs excluding the work item folder): 73020321f72996e6d22a3413ce7d87ec02fc83087c3b5c68d7fe031820669a46; the hash was recomputed before output and matched. The src/tests-only patch used by the children has SHA-256 e276f885cc7d778dfa709e0782ccfda0d75d979d043a2c5b927ca5923c77d11b.
- RULES: AGENTS.md / CLAUDE.md apply to all paths.

Intent: expose Garmin Training Readiness as `get_training_readiness`, with the shaping in `training_readiness_day` (`garmin/extract.py`), a thin tool in `tools/training_readiness.py` built on `per_day`, and a version bump to 0.7.0. The implementation matches the work item and plan. No scope creep was found.

Coverage ledger: 6 source files changed (`__init__.py`, `extract.py`, `tools/__init__.py`, `training_readiness.py`, 3 test files counted as source: 9 files in total), 280 changed lines. This is above the trivial limit, so every role was dispatched as a subagent. No role was covered inline. Dispatch/retry counts: 1 dispatch per role, 0 retries. All 7 roles returned status ok and covered every path they apply to.

## Checks

| Check | Command | Result |
|---|---|---|
| Install | `uv sync --locked` | exit 0 |
| Unit and e2e tests | `uv run pytest` (includes the end-to-end MCP client test) | exit 0, 89 passed |
| Lint | `uv run ruff check .` | exit 0, all checks passed |
| Format | `uv run ruff format --check .` | exit 0, 52 files already formatted |
| Type check / build | none declared by the project | not run: no such check is declared |

No check rewrote a tracked file. No database suite is declared and none was provided.

## Candidates

All candidates fall below the reporting threshold (confidence 75) and rely on payload shapes that Garmin is not shown to send. Cross-check: each describes either speculative input or a missing test for code whose behavior is correct as written.

| ID | Path:line | Category | Evidence | Conf. | Failure scenario | Baseline | Rule | Disposition |
|---|---|---|---|---|---|---|---|---|
| DCS-1 | src/my_garmin_mcp/garmin/extract.py:455 | edge case | The latest snapshot by timestamp is used even when it lacks score and level | 20 | A later empty snapshot drops the day; Garmin is not shown to send one | new code | none | rejected |
| EHS-1 | extract.py:432 | timestamp parsing | `_tr_time("2026-10-01")` returns "00:00" | 25 | Date-only `timestampLocal`; Garmin sends full datetimes | new code | none | rejected |
| EHS-2 | extract.py:459 | ordering | Snapshots are ordered by raw string comparison | 20 | Needs mixed or epoch timestamp formats; not shown reachable | new code | none | rejected |
| EHS-3 | extract.py:418 | serialization | `_tr_number` accepts NaN/inf | 10 | Garmin JSON cannot carry these; same pattern as other extractors | not a regression | none | rejected |
| TCS-1 | extract.py:445 | test gap | recovery and stress factor keys are not asserted | 70 | A key typo would pass all tests | new code | none | rejected (below threshold) |
| TCS-2 | extract.py:421 | test gap | epoch-ms `_tr_time` branch untested | 60 | numeric `timestampLocal` | new code | none | rejected |
| TCS-3 | extract.py:456 | test gap | score-only and level-only snapshots untested | 55 | guard change unnoticed | new code | none | rejected |
| TCS-4 | extract.py:454 | test gap | tie-break and empty-latest behavior untested | 45 | `reversed()` removed unnoticed | new code | none | rejected |

CCA, CCB, CSS and DBS returned no candidates. No `CHK` candidates: every check passed.

## Findings

No issues found. Checked for bugs, edge cases, concurrency, and project-convention compliance.
