# 6F8JA — Add SpO2 and respiration MCP tool(s)

> Captured: 2026-10-16 Type: Enhancement

## What

Expose Garmin SpO2 (blood oxygen) and respiration data through the MCP server, following the pattern of the existing per-day tools (`get_stress`, `get_body_battery`, `get_training_readiness`): one file per tool in `src/my_garmin_mcp/tools/` with a `register(server)` function wired up in `tools/__init__.py`, payload shaping as pure, unit-tested functions in `garmin/extract.py`, date handling via `garmin/dates.py`, and Garmin calls through `GarminClient.call`. Failures must be `ToolError`s (`GarminError`, `InvalidRequest`). Output is compact JSON to keep phone context small.

Whether this is one combined tool or two (`get_spo2`, `get_respiration`) is for the planning lane to decide after looking at what the `garminconnect` getters (SpO2 and respiration data per day) actually return. Include the end-to-end MCP client test, a version bump (`pyproject.toml`, `__version__`, `uv lock`), and doc updates per `docs/conventions/documentation.md`.

## Why

SpO2 and respiration are listed under "More Garmin data" in `work/future-improvements.md` as not yet exposed. They complete the overnight/recovery picture next to sleep, HRV, resting HR and stress, so Claude can answer questions about breathing and oxygen saturation trends from the phone app.

## Notes

- Check real payload shapes against the local dev server (see the `local-dev-env` skill) before settling on the output format; all-day series can be long, so consider summaries (avg/min/max, lowest SpO2) plus a downsampled series.
- Per-day tools make one Garmin request per day (3 at a time, max 31 days); keep to that limit.
- Remove the SpO2/respiration mention from `work/future-improvements.md` when done.

Depends on: none

## Outcome

> Implemented: 2026-10-16

Added two per-day tools, `get_spo2` and `get_respiration`, mirroring `get_stress`: one `per_day` request per day, pure extractors `spo2_day` and `respiration_day` in `garmin/extract.py`, and `MAX_DAYS_SPO2` / `MAX_DAYS_RESPIRATION` (7 days) in `garmin/dates.py`. Each returns a per-day summary plus a bucketed `[local time, value]` series (SpO2 60 min, respiration 30 min). Version bumped to 0.8.0; README, AGENTS.md and `work/future-improvements.md` updated.

### Deviations from the plan

- Payload keys could not be verified: `garminconnect` 0.3.17 only proxies the endpoints (`get_spo2_data`, `get_respiration_data`), so the plan's hypothesised keys were used unchanged. For SpO2 only the `spO2HourlyAverages` `[ts, value]` series is read; the `continuousReadingDTOList` dict-row fallback was not implemented. Missing summary keys are tolerated.
- Shared bucketing is a new private helper `_local_buckets` used by both new extractors; `stress_day` is untouched.
- `docs/architecture/overview.md` and the `local-dev-env` skill list no tools, so they were not edited.
- SpO2 bucket means are integers (`round(x)`), respiration means `round(x, 1)`.

### Validation

- `uv run ruff check .` — pass
- `uv run ruff format --check src tests` — pass (34 files); whole-repo check fails only on the plan markdown under `work/`
- `uv run pytest` — 118 passed (unit plus end-to-end MCP client test)
- `uv lock --check` — pass
- Manual check against a real Garmin account — not run (needs credentials)
