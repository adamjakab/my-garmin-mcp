# R367F — Add get_training_readiness MCP tool

> Captured: 2026-10-16 Type: Enhancement

## What

Add a `get_training_readiness` MCP tool that returns the owner's Garmin Training Readiness (score, level and its contributing factors) for a date or date range, backed by the `garminconnect` library via `GarminClient`.

It follows the pattern of the existing Garmin tools: a new file in `src/my_garmin_mcp/tools/` exposing `register(server)`, wired up in `tools/__init__.py`. Payload shaping goes in `garmin/extract.py` (pure, unit-tested) and date handling uses `garmin/dates.py`. The result is compact JSON text, and failures are raised as `ToolError`s (`GarminError`, `InvalidRequest`). Tests, the README tool list and the `CLAUDE.md` tool list are updated, and the version is bumped per the repo conventions.

## Why

Training readiness is listed under "Ideas for later" in `work/future-improvements.md` ("Training readiness and training status, ..."). It is a daily summary of how ready the body is for training, and it combines sleep, recovery, HRV and load. That makes it useful when asking Claude from the mobile app whether to train hard today. It complements the sleep, HRV and body battery tools already served.

## Notes

- Compact output matters because it is read on a phone.
- Reference implementations: `tools/stress.py` and `tools/body_battery.py` (most recent, same date-range style).
- Open for planning: which `garminconnect` method to call (expected `get_training_readiness`), and which fields to keep.
- Training status is a separate item in the same ideas bullet and is out of scope here.

Depends on: none

## Outcome

> Implemented: 2026-10-16

Added the `get_training_readiness` MCP tool (one request per day via `per_day`, calling `Garmin.get_training_readiness` through `GarminClient`). The pure `training_readiness_day` in `garmin/extract.py` picks the latest snapshot per day and returns score, level, short feedback, local time, sleep score, recovery minutes/phase and the five factors (percent and feedback). The tool is registered in `tools/__init__.py`, the README, `AGENTS.md` and `work/future-improvements.md` are updated, and the version is bumped to 0.7.0.

### Deviations from the plan

- No new `MAX_DAYS_TRAINING_READINESS` constant: the tool uses the existing `MAX_DAYS_PER_DAY_TOOLS` (31), as the sleep, HRV and resting HR tools do.
- README: besides the new row, the "Training readiness, training status | No" row became "Training status | No".
- `docs/` had no tool counts or lists needing change, so no "Last updated" dates were touched.
- The real payload's `timestampLocal` format is unconfirmed; `time` is parsed best effort and omitted on failure.

### Validation

- `uv run ruff check .` and `uv run ruff format --check .`: pass
- `uv run pytest tests/test_extract.py tests/test_tools.py tests/test_version.py`: 77 passed
- `uv run pytest tests/test_e2e.py`: 4 passed
- `uv lock --check`: pass
- Type check: none configured, not run. Manual validation against Garmin: not run (no credentials).
