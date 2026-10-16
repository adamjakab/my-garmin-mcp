# D30VF — Add get_stress MCP tool for all-day stress metrics

> Captured: 2026-10-15 Type: Enhancement

## What

Add an eleventh MCP tool, `get_stress`, exposing Garmin's all-day stress metrics through the `my_garmin_mcp` server. Like the existing Garmin tools (for example `get_body_battery` in `src/my_garmin_mcp/tools/body_battery.py`), it takes `start_date` and `end_date`, fetches data through the shared `GarminClient` (`garmin.call(lambda g: g.get_...(...))`), and returns compact JSON text. Per day it should give the summary values (overall/average and max stress, time spent in rest/low/medium/high stress where available) plus a downsampled list of `[local time, level]` readings, so the payload stays small for the phone.

## Why

Stress is one of the Garmin health signals not yet reachable from Claude, and it complements the existing sleep, HRV, resting heart rate, all-day heart rate and Body Battery tools when asking about recovery and load. The owner uses the server as a custom connector from Claude Code and the Claude mobile app, so the output must stay compact.

## Notes

- Follow the existing pattern: one file `src/my_garmin_mcp/tools/stress.py` with `register(server, garmin)`, wired up in `tools/__init__.py`; payload shaping as a pure, unit-tested function in `garmin/extract.py`; a range limit constant in `garmin/dates.py` (like `MAX_DAYS_BODY_BATTERY`) with `parse_range` and bounded parallelism if the library call is per-day.
- Failures must be `ToolError`s (`GarminError`, `InvalidRequest`).
- Check which `garminconnect` method fits (for example `get_stress_data` per day, and the multi-day variants) and the shape of its payload before fixing the output format.
- Update docs (README documentation index/tool list, CLAUDE.md/AGENTS.md tool list) per `docs/conventions/documentation.md`, bump the version in `pyproject.toml` and `__version__` and run `uv lock`, and extend the end-to-end MCP client test for the new tool.
- Open question for planning: exact output fields and sampling interval of the readings.

Depends on: none

## Outcome

> Implemented: 2026-10-16

Added the `get_stress` tool (`src/my_garmin_mcp/tools/stress.py`): per day, average and max stress, minutes in rest/low/medium/high and `[local time, level]` readings in 30-minute buckets, from `Garmin.get_stress_data`. Payload shaping is the pure `stress_day` in `garmin/extract.py`; the range limit is `MAX_DAYS_STRESS = 7` in `garmin/dates.py`. Version bumped to 0.6.0.

### Deviations from the plan

`stress_day` omits `bucket_minutes`, `columns` and `readings` when a day has a summary but no valid readings (the plan left this open).

### Validation

- `ruff check` and `ruff format --check`: pass
- `uv run pytest`: 75 passed (includes the end-to-end MCP client test)
- `uv lock --check`: pass
- Manual check against a live Garmin account: not run (needs credentials).
