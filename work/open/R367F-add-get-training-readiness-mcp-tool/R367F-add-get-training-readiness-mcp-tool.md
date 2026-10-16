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
