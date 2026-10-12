# UP4TN — Add MCP tool: all-day heart rate

> Captured: 2026-10-12 Type: Enhancement

## What

Add a new MCP tool that returns the all-day (intraday) heart rate for a Garmin day, following the pattern of the existing tools: a new file in `src/my_garmin_mcp/tools/` exposing `register(server, garmin)`, wired up in `tools/__init__.py`, with the payload shaping in `garmin/extract.py` (pure, unit-tested) and date handling in `garmin/dates.py`. The data comes from the `garminconnect` library through `GarminClient.call(...)`, as the other tools do (for example `get_resting_hr` uses `g.get_rhr_day`). The tool must return compact JSON text (the raw heart rate time series is large, so it needs downsampling or summarising, e.g. min/max/average plus bucketed readings) and raise `ToolError`s (`GarminError`, `InvalidRequest`) on failure.

## Why

The README coverage table lists "All-day heart rate" as "No", and `work/future-improvements.md` names daily and intraday heart rate as a gap. Only resting heart rate is available today, so Claude cannot answer questions about how heart rate behaved through a day (stress, workouts, sleep, recovery).

## Notes

- Keep the output small for phone context; decide the bucketing/summary shape during planning.
- Likely needs a single-day or short range limit (see `MAX_DAYS_PER_DAY_TOOLS`).
- On completion: update the README coverage table, add tests (extract unit tests and the end-to-end MCP client test), and bump the version in `pyproject.toml` and `__version__` in `src/my_garmin_mcp/__init__.py`, then run `uv lock`.

Depends on: none

## Outcome

> Implemented: 2026-10-12

Added the `get_heart_rate` tool (`src/my_garmin_mcp/tools/heart_rate.py`, registered in `tools/__init__.py`). It returns per-day min/max/resting/avg plus readings bucketed into local-time windows (default 30 min, 5-120 allowed) as `[HH:MM, min, max, avg]` rows, shaped by `heart_rate_day` in `garmin/extract.py`. A call covers at most 3 days (`MAX_DAYS_HEART_RATE` in `garmin/dates.py`). Version bumped to 0.4.0; the README coverage table is updated.

### Deviations from the plan

Also updated `AGENTS.md` (tool count "eight" → "nine" and the tool list) so it does not go stale; the plan made this conditional.

### Validation

- `ruff check` and `ruff format --check`: pass.
- `pytest` on test_extract, test_version, test_garmin_client, test_tools: 35 passed; `tests/test_e2e.py`: 4 passed.
- No type checker is configured.
- Not validated against real Garmin data (no credentials in this environment), so the payload shape (`heartRateValues`, `startTimestampGMT/Local`) is unverified against a live response.
