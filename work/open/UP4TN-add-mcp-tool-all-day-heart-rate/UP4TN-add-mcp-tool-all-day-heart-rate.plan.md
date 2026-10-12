# Implementation Plan: Add MCP tool: all-day heart rate

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

A new MCP tool `get_heart_rate` returns the all-day (intraday) heart rate for one to a few Garmin days: per-day min/max/resting values plus the readings bucketed into fixed time windows (min/max/avg per bucket), so the payload stays small for phone context. Data comes from `garminconnect`'s `Garmin.get_heart_rates(cdate)` through `GarminClient.call(...)`.

## User Story

As the owner of the Garmin account, talking to Claude from the mobile app
I want to ask how my heart rate behaved through a day
So that Claude can relate stress, workouts, sleep and recovery to the heart rate curve, not just the resting value.

## Problem Statement

Only resting heart rate is exposed (`get_resting_hr`). The README coverage table lists "All-day heart rate" as "No" and `work/future-improvements.md` names intraday heart rate as a gap. The raw series (a reading about every 2 minutes, ~720 pairs/day) is too large to pass through unreduced.

## Solution Statement

Mirror `get_resting_hr`: a thin tool file using `per_day(...)`, with a pure, unit-tested extractor `heart_rate_day` in `garmin/extract.py`. The extractor buckets `heartRateValues` into `bucket_minutes` windows (default 30, so 48 rows/day) as compact rows `[local "HH:MM", min, max, avg]`, mirroring the compact-row/`columns` shape of `bucket_details` in `extract.py`. A small new range constant `MAX_DAYS_HEART_RATE = 3` in `garmin/dates.py` keeps output bounded.

## Out of Scope / Non-Goals

- Not included: stress, body battery, steps, SpO2, respiration intraday series (separate items in `work/future-improvements.md`).
- Not included: heart rate zones / time-in-zone, or per-activity heart rate (already in `get_activity`).
- Not changing: `get_resting_hr`, `get_sleep` or any existing tool's output.
- Not changing: `GarminClient` (`garmin/client.py`) behaviour or error handling.

## Feature Metadata

**Feature Type**: New Capability (Enhancement per work item)
**Estimated Complexity**: Low
**Primary Systems Affected**: `tools/`, `garmin/extract.py`, `garmin/dates.py`, README, tests, version
**Dependencies**: `garminconnect` (already installed); no new libraries

## Related Work

**Implements**: work item `UP4TN-add-mcp-tool-all-day-heart-rate` (`work/open/UP4TN-add-mcp-tool-all-day-heart-rate/UP4TN-add-mcp-tool-all-day-heart-rate.md`) · **Feature**: none (standalone work item; `Depends on: none` confirmed, no change to the work item file needed)

**Back-references**:

- `work/future-improvements.md` (line 9) - Why: names intraday heart rate as a gap; remove that mention on completion.

**Forward-references**:

- (none yet)

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `src/my_garmin_mcp/tools/resting_hr.py` (all) - Why: the exact tool pattern to mirror (`per_day`, `as_json`, description with day cap).
- `src/my_garmin_mcp/tools/_common.py` (lines 9-27) - Why: `StartDate`, `EndDate`, `per_day(garmin, start, end, max_days, fetch, extract)` (drops falsy extract results), `as_json`.
- `src/my_garmin_mcp/tools/__init__.py` (all) - Why: add the module to the import and the `for module in (...)` tuple.
- `src/my_garmin_mcp/garmin/dates.py` (lines 7-11) - Why: the range-limit constants.
- `src/my_garmin_mcp/garmin/extract.py` (lines 1-16, 75-80, 172-208) - Why: `_clean`, `_local_iso` (Garmin "Local" ms timestamps are epoch ms shifted to local wall clock; format via UTC), `resting_hr`, and `bucket_details` (the compact `columns` + rows shape to mirror).
- `tests/test_extract.py` (lines 1-14, 55-62, 115-135) - Why: import list and test style for extractors.
- `tests/test_tools.py` (lines 14-60, 66-75) - Why: `FakeApi` (add `get_heart_rates`) and `session()` / `_data()` helpers for the in-process MCP client tests.
- `tests/test_e2e.py` (lines 58-75) - Why: hard-coded sorted tool-name list that must gain `get_heart_rate`.
- `README.md` (lines 19-20, 35) - Why: coverage table row "All-day heart rate | No" and tool list.
- `docs/conventions/versioning.md` - Why: version bump rules.

### New Files to Create

- `src/my_garmin_mcp/tools/heart_rate.py` - the `get_heart_rate` tool.

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- garminconnect source, `Garmin.get_heart_rates(cdate)` (installed in the uv venv after `uv sync`; find with `uv run python -c "import garminconnect;print(garminconnect.__file__)"`).
  - Why: confirm the payload. Expected shape (verify against a real or recorded response; it could not be fetched in the planning session): `{"calendarDate", "startTimestampGMT", "endTimestampGMT", "startTimestampLocal", "endTimestampLocal", "maxHeartRate", "minHeartRate", "restingHeartRate", "lastSevenDaysAvgRestingHeartRate", "heartRateValues": [[epoch_ms_GMT, bpm_or_null], ...]}`. Readings are every ~2 min; `bpm` is null when the watch was off or no reading.

### Patterns to Follow

**Naming**: tool `get_heart_rate`, file `tools/heart_rate.py`, extractor `heart_rate_day`, constant `MAX_DAYS_HEART_RATE`.

**Tool shape** (from `tools/resting_hr.py`):
```python
days = await per_day(garmin, start_date, end_date, MAX_DAYS_PER_DAY_TOOLS, lambda g, d: g.get_rhr_day(d), resting_hr)
return as_json({"start_date": start_date, "end_date": end_date, "count": len(days), "resting_hr": days})
```
For this tool the extractor needs `bucket_minutes`, so pass `lambda day, payload: heart_rate_day(day, payload, bucket_minutes)`.

**Error handling**: failures must be `ToolError`s. `GarminClient.call` raises `GarminError`; `parse_range` raises `InvalidRequest`. An out-of-range `bucket_minutes` must raise `InvalidRequest` (import from `..garmin.dates`) — any other exception shows Claude only "Error executing tool".

**Logging**: none needed in the tool (the client logs).

**Parameters**: annotate like `_common.StartDate` using `Annotated[int, Field(description=...)]`.

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation

Add `MAX_DAYS_HEART_RATE` to `garmin/dates.py`; add `heart_rate_day` to `garmin/extract.py`.

### Phase 2: Core Implementation

**Depends on:** Phase 1

Create `tools/heart_rate.py`.

### Phase 3: Integration

**Depends on:** Phase 2

Register in `tools/__init__.py`; README, future-improvements, version bump + `uv lock`.

### Phase 4: Testing & Validation

**Depends on:** Phase 2 (tests for the extractor can be written alongside Phase 1)

Extractor unit tests; in-process MCP tool tests; update the e2e tool-name list.

---

## STEP-BY-STEP TASKS

### UPDATE src/my_garmin_mcp/garmin/dates.py

- **IMPLEMENT**: add `MAX_DAYS_HEART_RATE = 3` next to the other limits, with the comment that each day returns a full time series.
- **PATTERN**: `dates.py:7-11`.
- **GOTCHA**: Auto-decided cap of 3 days (see Open Questions).
- **VALIDATE**: `uv run ruff check src`
- **SATISFIES**: AC #3

### ADD heart_rate_day to src/my_garmin_mcp/garmin/extract.py

- **IMPLEMENT**: `heart_rate_day(day: str, payload: dict | None, bucket_minutes: int = 30) -> dict | None`. Return `None` if no payload or no non-null readings in `heartRateValues` (so `per_day` drops the day). Otherwise return `_clean({"date": payload.get("calendarDate") or day, "resting_hr": payload.get("restingHeartRate"), "min_hr": payload.get("minHeartRate"), "max_hr": payload.get("maxHeartRate"), "avg_hr": <mean of readings, rounded to 1 dp>, "bucket_minutes": bucket_minutes, "columns": ["time", "min", "max", "avg"], "readings": [[ "HH:MM", min, max, round(avg)], ...]})`. Convert each reading's GMT ms to local wall-clock by adding offset `startTimestampLocal - startTimestampGMT` (ms; use 0 if either missing), then bucket by `(minutes_since_local_midnight // bucket_minutes) * bucket_minutes` and format as `HH:MM` (via `datetime.fromtimestamp(ms/1000, UTC)` as `_local_iso` does). Skip null/non-numeric readings; omit empty buckets; sort by time. Prefer `min_hr`/`max_hr` from the payload but fall back to the min/max of the readings.
- **PATTERN**: `extract.py:172-208` (`bucket_details`) for the compact columns/rows shape; `_clean`, `_local_iso`.
- **GOTCHA**: timestamps are GMT, not local, unlike the "...Local" fields; bucket keys must be local time-of-day. A day crossing midnight in GMT is why the offset is applied before bucketing.
- **VALIDATE**: `uv run pytest tests/test_extract.py -q`
- **SATISFIES**: AC #1, #2

### CREATE src/my_garmin_mcp/tools/heart_rate.py

- **IMPLEMENT**: `register(server, garmin)` defining `get_heart_rate(start_date: StartDate, end_date: EndDate, bucket_minutes: Annotated[int, Field(description="Bucket size in minutes (5-120), default 30")] = 30) -> str`. Name `get_heart_rate`, title "All-day heart rate", description stating the buckets, local times, and "At most {MAX_DAYS_HEART_RATE} days per call; days without data are left out." `ToolAnnotations(read_only_hint=True)`. Raise `InvalidRequest` if `bucket_minutes` not in 5..120 before any fetch. Fetch with `g.get_heart_rates(d)`. Return `as_json({"start_date":..., "end_date":..., "count": len(days), "heart_rate": days})`.
- **PATTERN**: `tools/resting_hr.py` (all).
- **IMPORTS**: `Annotated`, `pydantic.Field`, `MCPServer`, `ToolAnnotations`, `GarminClient`, `InvalidRequest`, `MAX_DAYS_HEART_RATE`, `heart_rate_day`, `EndDate, StartDate, as_json, per_day`.
- **GOTCHA**: Validate `bucket_minutes` so it divides sensibly; 5..120 range only (no divisibility requirement).
- **VALIDATE**: `uv run ruff check src && uv run ruff format --check src`
- **SATISFIES**: AC #1, #3, #4

### UPDATE src/my_garmin_mcp/tools/__init__.py

- **IMPLEMENT**: import `heart_rate` and add it to the module tuple.
- **PATTERN**: `tools/__init__.py:5-10`.
- **VALIDATE**: `uv run python -c "import my_garmin_mcp.tools"`
- **SATISFIES**: AC #1

### UPDATE tests/test_extract.py

- **IMPLEMENT**: tests for `heart_rate_day`: bucketing and local-time offset (e.g. GMT start with +2h local offset → first bucket label in local time); null readings skipped; empty/None payload and all-null values → `None`; min/max fallback; different `bucket_minutes`.
- **PATTERN**: `tests/test_extract.py:55-62, 115-135`.
- **VALIDATE**: `uv run pytest tests/test_extract.py -q`
- **SATISFIES**: AC #2, #5

### UPDATE tests/test_tools.py and tests/test_e2e.py

- **IMPLEMENT**: add `get_heart_rates(self, day)` to `FakeApi` (record call, return a small payload; return `{"heartRateValues": []}` for a day ending `-02`). Tests: valid call returns bucketed `heart_rate` and skips the empty day; `bucket_minutes=1` and a 4-day range each return an error result (`result.is_error`). Add `"get_heart_rate"` to the name list in `test_e2e.py:62-71`.
- **PATTERN**: `tests/test_tools.py:59-66` (sleep test), `:69-72` (bad range).
- **VALIDATE**: `uv run pytest tests/test_tools.py tests/test_e2e.py -q`
- **SATISFIES**: AC #4, #5

### UPDATE README.md, work/future-improvements.md

- **IMPLEMENT**: README row "All-day heart rate | Yes (`get_heart_rate`)"; list the tool wherever the README or `docs/` enumerates tools (grep for `get_resting_hr`); remove "daily and intraday heart rate" from `future-improvements.md:9` or narrow it. Also update `AGENTS.md` tool count/list ("eight tools", the tool list in Architecture) only if the project's documentation rules in `docs/conventions/documentation.md` require it — read it first.
- **VALIDATE**: `grep -rn "get_resting_hr" README.md docs AGENTS.md`
- **SATISFIES**: AC #6

### UPDATE version (pyproject.toml, src/my_garmin_mcp/__init__.py, uv.lock)

- **IMPLEMENT**: bump 0.3.2 → 0.4.0 (new tool) in both places, then `uv lock`.
- **PATTERN**: `docs/conventions/versioning.md`.
- **VALIDATE**: `uv run pytest tests/test_version.py -q`
- **SATISFIES**: AC #6

---

## TESTING STRATEGY

pytest (async mode already configured) with in-process fakes; no network.

### Unit Tests

`tests/test_extract.py` for `heart_rate_day` as above.

### Integration Tests

`tests/test_tools.py` (in-process MCP client via `FakeApi`) and `tests/test_e2e.py` (tool list only; run those two files by name).

### Edge Cases

- Day with no readings / all-null readings → dropped.
- Missing `startTimestampLocal`/`GMT` → offset 0.
- Readings before local midnight vs after (offset crossing the day boundary).
- `bucket_minutes` out of range → `InvalidRequest`.
- Range > 3 days → `InvalidRequest`.
- Garmin failure → `GarminError` (covered by existing client tests).

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style

`uv run ruff check . && uv run ruff format --check .`

### Level 2: Unit Tests

`uv run pytest tests/test_extract.py tests/test_version.py tests/test_garmin_client.py -q`

### Level 3: Integration Tests

`uv run pytest tests/test_tools.py -q` and `uv run pytest tests/test_e2e.py -q`

### Level 4: Manual Validation

`.claude/skills/local-dev-env/scripts/server.sh restart`, then call `get_heart_rate` for yesterday through the Garmin-MCP-Local tools (see the `local-dev-env` skill) and check size (~48 rows/day) and that local times match the Garmin app. This also verifies the assumed payload shape.

### Level 5: Additional Validation (Optional)

None.

---

## ACCEPTANCE CRITERIA

- [ ] `get_heart_rate(start_date, end_date, bucket_minutes=30)` returns per-day min/max/resting/avg plus bucketed local-time readings as compact JSON.
- [ ] Days without readings are omitted; null readings ignored.
- [ ] Range limited to 3 days and `bucket_minutes` to 5-120, both as `InvalidRequest` tool errors.
- [ ] Registered and listed by the server (`test_e2e.py` list updated).
- [ ] Extractor unit tests and in-process tool tests added and passing; ruff clean.
- [ ] README coverage table, future-improvements and version (both files + `uv.lock`) updated.

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately
- [ ] Ruff and the test files above pass
- [ ] Manual check against the real/local server
- [ ] Acceptance criteria all met

---

## OPEN QUESTIONS / ASSUMPTIONS

- Auto-decided — Day cap: 3 days (`MAX_DAYS_HEART_RATE`), not the 31 of `MAX_DAYS_PER_DAY_TOOLS` — a new constant, trivially raised later; output ~48 rows/day.
- Auto-decided — Bucket shape: default 30 min, caller-adjustable 5-120, rows `[HH:MM, min, max, avg]` — contained to this tool's output, cheap to change.
- Auto-decided — Parameters reuse `start_date`/`end_date` like sibling tools instead of a single `date` — consistency; one day = same start and end.
- Auto-decided — Version bump minor (0.4.0) — a new tool; reversible.
- Assumed — `get_heart_rates` payload shape as described above (field names and GMT timestamps) could not be verified in this session (no installed library or Garmin access); the executor must check the installed `garminconnect` source and the manual run, and adjust the extractor if names differ.

## NOTES (open canvas)

- Rejected: returning the raw ~720 readings/day (too large for phone context); rejected a single summary with no time series (would not answer "how did it behave through the day").
- Rejected: reusing `bucket_details` — it works on activity metric descriptors, not `[ts, bpm]` pairs.
- Output estimate: 48 rows x ~20 bytes ≈ 1 KB/day.

## AMENDMENTS

