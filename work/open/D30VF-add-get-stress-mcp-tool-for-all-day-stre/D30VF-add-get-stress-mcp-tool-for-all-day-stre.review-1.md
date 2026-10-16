# Review 1: Add get_stress MCP tool for all-day stress metrics

**Verdict: PASS.** No candidate reached the 75-confidence threshold. The sub-threshold items below are non-blocking notes.

## Summary

The change adds the `get_stress` tool (`src/my_garmin_mcp/tools/stress.py`), the pure `stress_day` extractor in `src/my_garmin_mcp/garmin/extract.py`, `MAX_DAYS_STRESS = 7` in `src/my_garmin_mcp/garmin/dates.py`, registration in `tools/__init__.py`, tests, docs, and a version bump to 0.6.0. It follows the one-file-per-tool pattern and reuses `per_day`. No scope creep was found. Both convention roles found no violations.

## Scope

- SCOPE_ID: `D30VF-2634bd6..309ddb4`
- REPOSITORY_ROOT: `/tmp/dev-dashboard-run/repo`
- BASELINE: `2634bd6c0943763ee0b1e02e86ae5c0d36f07af4` (`git merge-base main HEAD`)
- IMPLEMENTATION: `309ddb48cc50697570b485dcff8bb5e7cae25f90`
- DIFF_SOURCE: `git diff --find-renames <baseline> <implementation>`, review-N reports excluded
- Frozen patch (src, tests, pyproject.toml): SHA-256 `ae640f2efa0cf8b7cc2846fb7d8a18d7ab8d9ad0d6fda00114b25e0461621f9b`
- Limitation: per-entry snapshot hashes were not computed, only the patch hash.
- Changed paths: AGENTS.md, README.md, pyproject.toml, uv.lock, `src/my_garmin_mcp/__init__.py`, `garmin/dates.py`, `garmin/extract.py`, `tools/__init__.py`, `tools/stress.py` (new), `tests/test_e2e.py`, `tests/test_extract.py`, `tests/test_tools.py`, `work/future-improvements.md`, and the work item plan and report.
- Source files changed (excluding docs, lockfile, work folder): 8 files (5 src, 3 tests); about 255 changed lines. This is above the trivial threshold, so every role was dispatched as a subagent.

## Checks

Run at the pinned implementation from the lockfile.

| Command | Exit | Result |
|---|---|---|
| `uv sync --locked` | 0 | installed |
| `uv run pytest` | 0 | 75 passed (includes the end-to-end MCP client test) |
| `uv run ruff check .` | 0 | All checks passed |
| `uv run ruff format --check .` | 0 | 50 files already formatted |
| type check | not run | the project declares none |

No tracked file was rewritten. No `CHK` candidates.

## Detection coverage

| Role | How | Status | Result |
|---|---|---|---|
| CCA | subagent | complete | no candidates |
| CCB | subagent | complete | no candidates |
| DCS | subagent | complete | DCS-1 |
| CSS | subagent | complete | CSS-1 |
| EHS | subagent | complete | EHS-1..5 |
| DBS | subagent | complete | DBS-1 |
| TCS | subagent | complete | TCS-1..3 |

No role was covered inline. A stray subagent with a placeholder prompt was launched by mistake; it did nothing and is not counted. Cross-check and validation were done by the parent session (see below), not by subagents.

## Candidates

Cross-check: the strongest argument against each timestamp or duration candidate is that Garmin does not send non-finite or out-of-range values and that `heart_rate_day` and `body_battery_days` use the same unguarded `datetime.fromtimestamp` call, so the exposure is not new. Validation: I reproduced EHS-1, EHS-2 and EHS-3 by running `stress_day` directly (`[[nan, 5]]` raises `ValueError`; `restStressDuration=nan` raises `ValueError`; `[[1e30, 5]]` raises `OverflowError`). The behaviour is real but needs a malformed upstream payload, so no reachable production trigger is shown. EHS-1 is re-scored from 55 to 50 for that reason; the others are unchanged.

| ID | Path:line | Category | Confidence | Failure scenario | Baseline comparison | Disposition |
|---|---|---|---|---|---|---|
| EHS-1 | `extract.py:372` | exception propagation | 50 (was 55) | A NaN, infinite or out-of-range timestamp raises and fails the whole multi-day call, contradicting "odd payloads never raise". | Same call exists in `heart_rate_day` and `body_battery_days`; the docstring claim is new. | rejected (below 75) |
| EHS-3 | `extract.py:345` | malformed input | 45 | NaN, infinite or huge duration raises in `round(seconds / 60)`. Reproduced. | New helper; `_stress_level` rejects the same values. | rejected |
| EHS-2 | `extract.py:128` | malformed input | 40 | Extreme start timestamps give an overflowing offset. | `_epoch_ms` is pre-existing. | rejected |
| TCS-1 | `extract.py:344` | untested branch | 40 | Dropping the negative or bool check in `_stress_minutes` would not fail a test. | Levels have explicit negative cases; durations do not. | rejected |
| CSS-1 | `garmin/client.py:117` | shared state | 35 | Concurrent auth failures in one parallel batch can reach `MAX_AUTH_FAILURES` and delete the token file. | Pre-existing `GarminClient` and `per_day` design; no new shared state in this diff. | rejected |
| TCS-2 | `extract.py:366` | untested branch | 25 | Offset fallback when only one start timestamp parses is untested. | None. | rejected |
| DBS-1 | `extract.py:369` | robustness | 20 | Same overflow as EHS-1. | Pre-existing pattern. | rejected |
| TCS-3 | `dates.py:12` | boundary | 20 | A 7-day range, the limit, is untested. | `per_day` boundary logic is shared and tested elsewhere. | rejected |
| EHS-4 | `extract.py:398` | type validation | 15 | A non-string `calendarDate` passes through. | Same pattern at lines 65, 79 and 116. | rejected |
| EHS-5 | `extract.py:351` | boundary | 10 | `bucket_minutes=0` raises; the tool never passes it. | Same as `heart_rate_day`. | rejected |
| DCS-1 | `extract.py:372` | robustness | 5 | Same overflow as EHS-1; no reachable trigger. | Pre-existing pattern. | rejected |

## Non-blocking notes

- Guard `datetime.fromtimestamp` and `_stress_minutes` against non-finite values, or soften the "odd payloads never raise" docstring (EHS-1 to EHS-3, DBS-1, DCS-1).
- Add tests for invalid durations, a single parseable start timestamp, and a 7-day range (TCS-1 to TCS-3).
- `CSS-1` is a pre-existing `GarminClient` concern, not specific to this item.

## Findings

No issues found. Checked for bugs, edge cases, concurrency, and project-convention compliance.
