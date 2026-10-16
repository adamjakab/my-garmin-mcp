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
