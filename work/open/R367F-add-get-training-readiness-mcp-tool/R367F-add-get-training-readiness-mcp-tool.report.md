# Implementation Report — Add get_training_readiness MCP tool

**Plan**: `work/open/R367F-add-get-training-readiness-mcp-tool/R367F-add-get-training-readiness-mcp-tool.plan.md` **Branch**: wi/4-add-get-training-readiness-mcp-tool **Status**: COMPLETE

## Summary

Added the `get_training_readiness` tool (one request per day via `per_day`, `Garmin.get_training_readiness`). The pure `training_readiness_day` in `garmin/extract.py` picks the latest snapshot per day and returns score, level, short feedback, local time, sleep score, recovery minutes/phase and the five factors (pct + feedback). Docs updated and version bumped to 0.7.0.

## Tasks completed

- Range limit → `src/my_garmin_mcp/garmin/dates.py` (no change, see Deviations)
- `training_readiness_day` → `src/my_garmin_mcp/garmin/extract.py` (UPDATE)
- Tool → `src/my_garmin_mcp/tools/training_readiness.py` (CREATE)
- Registration → `src/my_garmin_mcp/tools/__init__.py` (UPDATE)
- Tests → `tests/test_extract.py`, `tests/test_tools.py`, `tests/test_e2e.py` (UPDATE)
- Docs/version → `README.md`, `AGENTS.md`, `work/future-improvements.md`, `pyproject.toml`, `src/my_garmin_mcp/__init__.py`, `uv.lock`

## Tests added

- `tests/test_extract.py`: latest snapshot and factor mapping, single dict, score 0 kept, empty/odd payloads give None, odd types and bad `timestampLocal` never raise.
- `tests/test_tools.py` (`FakeApi.get_training_readiness`): returns days and skips empty, one request per day, rejects long range and bad date.
- `tests/test_e2e.py`: tool name added to the expected list.

## Validation results

- `uv run ruff check . && uv run ruff format --check .` — pass
- `uv run pytest tests/test_extract.py tests/test_tools.py tests/test_version.py -q` — 77 passed
- `uv run pytest tests/test_e2e.py -q` — 4 passed (run by file; it is the one e2e file changed on this branch)
- `uv lock --check` — pass
- Type check: the project configures none; not run.
- Level 4 manual validation: not run (no Garmin credentials).

## Deviations from the plan

- No new `MAX_DAYS_TRAINING_READINESS` constant: the tool uses the existing `MAX_DAYS_PER_DAY_TOOLS` (31), which the plan allowed and which sleep/HRV/resting HR mirror.
- README: besides adding the new row, the "Training readiness, training status | No" row became "Training status | No".
- `docs/` contained no tool counts or lists needing change, so no "Last updated" dates were touched.

## Issues encountered

none. The real payload's `timestampLocal` format is unconfirmed; `time` is parsed best effort and omitted on failure.
