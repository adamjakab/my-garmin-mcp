# IU6OO — Add get_daily_summary MCP tool (steps, floors, intensity minutes)

> Captured: 2026-10-16 Type: Enhancement

## What

Add a new MCP tool `get_daily_summary` that returns, per day over a date range, Garmin's daily activity summary: step count and step goal, distance, floors climbed (and floor goal), intensity minutes (moderate, vigorous, goal) and, where compact, related daily totals such as calories. It follows the existing tool pattern: a new `src/my_garmin_mcp/tools/daily_summary.py` exposing `register(server, garmin)`, wired up in `tools/__init__.py`. The payload shaping goes in a pure, unit-tested function in `garmin/extract.py`, and the range limit (a `MAX_DAYS_*` constant) goes in `garmin/dates.py`. It uses `per_day` from `tools/_common.py` with the shared `GarminClient`. Output is compact JSON, days without data are left out, and failures are `ToolError`s.

## Why

The server covers sleep, HRV, heart rate, stress, SpO2 and more, but not the basic daily movement numbers (steps, floors, intensity minutes). Those are the first thing asked about activity and goal progress from the Claude mobile app, and they are not available from any current tool.

## Notes

- Likely `garminconnect` source: `get_user_summary(date)` (daily stats) and possibly `get_steps_data`. Check which fields are present and keep only the compact, useful ones for phone context.
- Follow the recent additions, e.g. `get_spo2` / `get_respiration` (work/implemented/2026-10-16-add-spo2-and-respiration-mcp-tool-s.md), including tests (extract unit tests plus the end-to-end MCP client test's tool list).
- Version bump per CLAUDE.md: `pyproject.toml` and `__version__` in `src/my_garmin_mcp/__init__.py`, then `uv lock`. Update the docs listing tools (README, CLAUDE.md tool count/list).
- Open question for planning: whether to also expose intraday step buckets or only daily totals (default: daily totals only).

Depends on: none
