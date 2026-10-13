# HLB9Q — Add MCP tool: body battery

> Captured: 2026-10-13 Type: Enhancement

## What

Add a ninth Garmin tool, `get_body_battery`, to the my-garmin-mcp server. It returns the owner's Garmin Body Battery data for a date or date range, backed by the `garminconnect` getters (e.g. `get_body_battery`, and `get_body_battery_events` if useful). It follows the existing tool pattern: a `register(server)` file in `src/my_garmin_mcp/tools/`, wired up in `tools/__init__.py`; payload shaping as pure, unit-tested code in `garmin/extract.py`; date handling and range limits via `garmin/dates.py`; calls through `GarminClient.call`; compact JSON text output; failures raised as `ToolError`s (`GarminError`, `InvalidRequest`).

The output should stay compact for phone context: per-day summary (e.g. highest, lowest, start/end of day, charged/drained totals) rather than the full raw time series, unless the plan decides a downsampled series is worth including.

## Why

Body Battery is one of the headline Garmin recovery metrics and is listed under "More Garmin data" in `work/future-improvements.md` as not yet exposed. Sleep, HRV, resting HR and heart rate are already available, so body battery completes the picture of recovery/energy for Claude to reason about.

## Notes

- Bump the version in `pyproject.toml` and `__version__` in `src/my_garmin_mcp/__init__.py`, then run `uv lock` (previous tool work bumped the minor version).
- Update the tool count/list in README.md, CLAUDE.md/AGENTS.md and any docs listing tools; remove body battery from `work/future-improvements.md`.
- Extend the end-to-end MCP client test and add unit tests for the extractor. Real Garmin response shapes are unverified here; the plan should check the `garminconnect` return format and handle days with missing data.
- Open design points for the plan: single date vs range (per-day tools make one request per day, max 31 days, 3 in parallel), and the exact fields to return.

Depends on: none

## Outcome

> Implemented: 2026-10-13

Added the `get_body_battery` tool. It makes one `Garmin.get_body_battery(start, end)` request for the whole range (max 31 days, `MAX_DAYS_BODY_BATTERY`) and reduces each day with the pure extractor `body_battery_days` in `garmin/extract.py` (highest, lowest, start, end, charged, drained, plus a 2-hourly `[time, level]` series). Version bumped to 0.5.0; README, AGENTS.md and `work/future-improvements.md` updated.

### Deviations from the plan

- Added an optional `factory` parameter to the `session()` test helper so the one-call test can inspect the fake API's calls.
- ISO-string timestamps are handled through a small `_epoch_ms` helper (numbers or ISO strings, else offset 0).

### Validation

- `uv run ruff check .` and `ruff format --check .`: pass
- `uv lock --check`: pass
- `uv run pytest` on `test_extract.py`, `test_version.py`, `test_garmin_client.py`, `test_tools.py`: 51 passed
- `uv run pytest tests/test_e2e.py`: 4 passed
- No type checker configured. Live-data check not run (no credentials), so the real Garmin payload shape is unverified.
