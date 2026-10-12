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
