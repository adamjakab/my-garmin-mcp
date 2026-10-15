# Implementation Plan: Add get_stress MCP tool for all-day stress metrics

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Add an eleventh MCP tool, `get_stress`, to the `my_garmin_mcp` server. For each day in a range it returns Garmin's all-day stress summary (overall/average and max stress level, minutes in rest/low/medium/high stress) plus a downsampled list of `[local time, level]` readings. Output is compact JSON text so it stays small on the phone.

## User Story

As the owner using Claude Code or the Claude mobile app
I want to ask Claude for my all-day stress data over a date range
So that Claude can reason about recovery and load together with sleep, HRV, resting HR, heart rate and Body Battery

## Problem Statement

Stress is one of the Garmin health signals not yet reachable through the server (README "Garmin coverage" says `Stress | No`; `work/future-improvements.md` lists `get_stress_data`).

## Solution Statement

Mirror `get_heart_rate` (per-day request via `per_day` in `tools/_common.py`, calling `Garmin.get_stress_data(iso_day)`) and `get_body_battery` (summary + coarse `[time, level]` series). Payload shaping lives in a new pure function `stress_day` in `garmin/extract.py`; the range limit is a new constant `MAX_DAYS_STRESS` in `garmin/dates.py`; the tool is `tools/stress.py`, registered in `tools/__init__.py`.

## Out of Scope / Non-Goals

- Not included: steps, respiration, SpO2 or the other "More Garmin data" items (separate work items).
- Not included: the stress-related `bodyBatteryValuesArray` inside the stress payload (the `get_body_battery` tool already covers it).
- Not included: a user-tunable bucket size parameter (see Auto-decided below; can be added later like `get_heart_rate.bucket_minutes`).
- Not included: the multi-day `get_stress_data` variants / weekly stress (`get_all_day_stress` or similar, if the installed library has them); only the per-day call.
- Not changing: existing tools, auth, `GarminClient`.

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: Low
**Primary Systems Affected**: `tools/`, `garmin/extract.py`, `garmin/dates.py`, tests, docs
**Dependencies**: `garminconnect` 0.3.17 (already locked in `uv.lock`); no new dependency

## Related Work

**Implements**: work item `D30VF-add-get-stress-mcp-tool-for-all-day-stre` (`work/open/D30VF-add-get-stress-mcp-tool-for-all-day-stre/D30VF-add-get-stress-mcp-tool-for-all-day-stre.md`) · **Feature**: none (standalone work item; nothing to inherit). Work item's `Depends on:` is `none`, and the analysis found no hard dependency.

**Back-references**:

- `work/implemented/2026-10-13-add-mcp-tool-body-battery.md` - Why: same shape of work (new tool + extractor + range limit + docs + version bump); mirror its outcome, including the `_epoch_ms` helper and the 0.5.0 bump.
- `work/implemented/2026-10-12-add-mcp-tool-all-day-heart-rate.md` - Why: per-day request with local-time bucketing, the closest extractor to mirror.

**Forward-references**:

- (none yet)

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `src/my_garmin_mcp/tools/heart_rate.py` (whole file) - Why: per-day tool using `per_day(...)` with `fetch`/`extract` lambdas and the `{"start_date", "end_date", "count", <key>: days}` response shape. Mirror this.
- `src/my_garmin_mcp/tools/body_battery.py` (whole file) - Why: description wording style ("At most N days per call; days without data are left out.") and `ToolAnnotations(read_only_hint=True)`.
- `src/my_garmin_mcp/tools/_common.py` (lines 8-27) - Why: `StartDate`, `EndDate`, `per_day`, `as_json`.
- `src/my_garmin_mcp/tools/__init__.py` - Why: the module tuple in `register_tools` to extend, plus the import line.
- `src/my_garmin_mcp/garmin/dates.py` (lines 7-13) - Why: range-limit constants (`MAX_DAYS_HEART_RATE = 3`, `MAX_DAYS_BODY_BATTERY = 31`) and `CONCURRENCY`; `parse_range`, `InvalidRequest`.
- `src/my_garmin_mcp/garmin/extract.py` (`_clean` line 7, `_local_iso` line 11, `heart_rate_day` lines 83-125, `_epoch_ms` ~line 128, `body_battery_days` ~152-210) - Why: patterns for the local-time offset (`startTimestampLocal - startTimestampGMT`), robust handling of malformed rows (never raise), `None` for a day with no data.
- `tests/test_extract.py` (lines ~196-300) - Why: extractor test style (helper builder, offset test, malformed rows, empty payload parametrize).
- `tests/test_tools.py` (`FakeApi` lines 15-75, `session` line 81, `_data` line 93, heart-rate tests ~152-170) - Why: add a `get_stress_data` fake and tool tests.
- `tests/test_e2e.py` (tool-name list, ~lines 60-73) - Why: the sorted list of expected tool names must include `get_stress`.
- `docs/conventions/documentation.md`, `docs/conventions/versioning.md` - Why: doc and version-bump rules.
- `README.md` (Garmin coverage table, line ~37 `| Stress | No |`), `AGENTS.md` (lines 7 and 29), `work/future-improvements.md` (line 9) - Why: docs to update.

### New Files to Create

- `src/my_garmin_mcp/tools/stress.py` - the tool.

(Extractor tests go in the existing `tests/test_extract.py`; tool tests in the existing `tests/test_tools.py`.)

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- The installed `garminconnect` source: after `uv sync`, read `.venv/lib/python3.*/site-packages/garminconnect/__init__.py`, searching `stress`. Why: the library was not installed when this plan was written, so the method name and payload below come from knowledge of the library, not from reading it. **Verify first**: `get_stress_data(cdate: str)` (GET `wellness-service/wellness/dailyStress/{cdate}`), and whether newer-named variants exist.
- Expected payload (to verify; real shape unconfirmed, no credentials here): a dict with `calendarDate`, `startTimestampGMT`/`startTimestampLocal` (epoch ms, or ISO strings in some payloads, hence `_epoch_ms`), `endTimestampGMT`/`endTimestampLocal`, `maxStressLevel`, `avgStressLevel`, `overallStressLevel`, `restStressDuration`, `lowStressDuration`, `mediumStressDuration`, `highStressDuration` (seconds), `stressValuesArray` = `[[epoch ms GMT, level], ...]` roughly every 3 minutes, and `bodyBatteryValuesArray` (ignore). Level 0-100; negative values (-1 unmeasurable/off wrist, -2 too much motion) and `null` mean "no reading" and must be dropped.

### Patterns to Follow

**Naming Conventions:** tool `get_stress`, module `tools/stress.py`, extractor `stress_day` (like `heart_rate_day`), constant `MAX_DAYS_STRESS`. Response key `"stress"`.

**Error Handling:** only `GarminError` (raised by `GarminClient.call`) and `InvalidRequest` (from `parse_range`) leave the tool; extractors never raise on odd payloads, they return `None`.

**Tool shape (from `heart_rate.py`):**

```python
days = await per_day(garmin, start_date, end_date, MAX_DAYS_HEART_RATE,
                     lambda g, d: g.get_heart_rates(d), lambda day, payload: heart_rate_day(day, payload, bucket_minutes))
return as_json({"start_date": start_date, "end_date": end_date, "count": len(days), "heart_rate": days})
```

**Extractor shape:** `_clean({...})` to drop `None`; `columns` + `readings` rows as in `heart_rate_day`.

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation

Verify the library method and payload (read the installed source), then add `MAX_DAYS_STRESS` to `garmin/dates.py`.

### Phase 2: Core Implementation

**Depends on:** Phase 1

Write `stress_day` in `garmin/extract.py` and the tool in `tools/stress.py`.

### Phase 3: Integration

**Depends on:** Phase 2

Register in `tools/__init__.py`; update docs; bump version and `uv lock`.

### Phase 4: Testing & Validation

**Depends on:** Phase 2 (tests can be written alongside)

Extractor unit tests, tool tests with a `FakeApi.get_stress_data`, e2e tool list.

---

## STEP-BY-STEP TASKS

### RUN uv sync and inspect garminconnect

- **IMPLEMENT**: `uv sync`, then grep `stress` in the installed `garminconnect/__init__.py`. Confirm `Garmin.get_stress_data(cdate)` exists and its endpoint. If the method name or payload keys differ from the "Expected payload" above, adapt the extractor keys accordingly and note it in the work item's Outcome.
- **GOTCHA**: the real response shape is unverified in this repo (no credentials); keep the extractor tolerant, as `body_battery_days` is.
- **VALIDATE**: `uv run python -c "import garminconnect; print(hasattr(garminconnect.Garmin, 'get_stress_data'))"`
- **SATISFIES**: AC #1

### UPDATE src/my_garmin_mcp/garmin/dates.py

- **IMPLEMENT**: add `MAX_DAYS_STRESS = 7  # one request per day, each day carries a time series` next to `MAX_DAYS_HEART_RATE`.
- **PATTERN**: `dates.py:10-12`
- **VALIDATE**: `uv run ruff check src`
- **SATISFIES**: AC #3

### ADD stress_day to src/my_garmin_mcp/garmin/extract.py

- **IMPLEMENT**: `def stress_day(day: str, payload: dict[str, Any] | None, bucket_minutes: int = 30) -> dict[str, Any] | None`. Return `None` unless `payload` is a dict with at least one valid reading or a summary value. Output (via `_clean`):
  - `date`: `payload.get("calendarDate") or day`
  - `avg_stress`: `avgStressLevel` (fall back to `overallStressLevel`, then the mean of valid readings); `max_stress`: `maxStressLevel` (fall back to max of readings). Treat negative summary values as missing.
  - `rest_min`, `low_min`, `medium_min`, `high_min`: the `*StressDuration` seconds divided by 60, rounded to int; omit when missing.
  - `bucket_minutes`, `columns: ["time", "level"]`, `readings`: rows `["HH:MM", mean level in bucket rounded to int]` per bucket of valid readings, sorted by time.
  - Offset: `_epoch_ms(startTimestampLocal) - _epoch_ms(startTimestampGMT)`, else 0, same as `body_battery_days`; shift each reading's epoch ms by it and take the UTC clock time (as `heart_rate_day` does).
  - Valid reading: a list/tuple of length >= 2, numeric non-bool timestamp, numeric non-bool level with `0 <= level <= 100`. Everything else is skipped silently.
- **PATTERN**: `heart_rate_day` (bucketing, `columns`/`readings`), `body_battery_days` (offset via `_epoch_ms`, never raising).
- **GOTCHA**: bucket-average downsampling hides short peaks, so also keep `max_stress` from the Garmin summary. Level 0 is a valid reading (rest); negatives are not.
- **VALIDATE**: `uv run pytest tests/test_extract.py -q`
- **SATISFIES**: AC #1, #2

### CREATE src/my_garmin_mcp/tools/stress.py

- **IMPLEMENT**: `register(server, garmin)` defining `get_stress(start_date: StartDate, end_date: EndDate) -> str`, `name="get_stress"`, `title="All-day stress"`, description naming the fields (average and max stress 0-100, minutes in rest/low/medium/high, `[local time, level]` readings per 30-minute bucket) and `f"At most {MAX_DAYS_STRESS} days per call; days without data are left out."`, `ToolAnnotations(read_only_hint=True)`. Body uses `per_day(garmin, start_date, end_date, MAX_DAYS_STRESS, lambda g, d: g.get_stress_data(d), stress_day)`; returns `as_json({"start_date", "end_date", "count", "stress": days})`.
- **PATTERN**: `tools/heart_rate.py`
- **IMPORTS**: `MCPServer`, `ToolAnnotations`, `GarminClient` from `..garmin`, `MAX_DAYS_STRESS` from `..garmin.dates`, `stress_day` from `..garmin.extract`, `EndDate, StartDate, as_json, per_day` from `._common`.
- **VALIDATE**: `uv run ruff check src && uv run ruff format --check src`
- **SATISFIES**: AC #1, #3

### UPDATE src/my_garmin_mcp/tools/__init__.py

- **IMPLEMENT**: add `stress` to the import list (alphabetical, after `sleep`) and to the module tuple in `register_tools`.
- **VALIDATE**: `uv run python -c "import my_garmin_mcp.tools"`
- **SATISFIES**: AC #1

### UPDATE tests/test_extract.py

- **IMPLEMENT**: tests for `stress_day`: summarises and buckets (mean per bucket, durations to minutes); applies the local offset (GMT 0 / local +3h gives `03:00`); drops negative, null, bool and malformed rows; falls back to computed avg/max when summary keys are missing; returns `None` for `None`, `{}`, non-dict, and an all-invalid series with no summary; custom `bucket_minutes`.
- **PATTERN**: `tests/test_extract.py:196-300`
- **VALIDATE**: `uv run pytest tests/test_extract.py -q`
- **SATISFIES**: AC #2, #4

### UPDATE tests/test_tools.py

- **IMPLEMENT**: add `FakeApi.get_stress_data(self, day)` appending `f"stress {day}"` to `calls`; returns a payload for normal days and `{}`/empty series for days ending `-02`. Tests: `get_stress` over 2026-10-01..03 returns days 01 and 03 with expected `readings`, `count == 2`, and one call per day; a range over `MAX_DAYS_STRESS` and a bad date are `is_error`.
- **PATTERN**: `tests/test_tools.py:30-39` and `152-168`
- **VALIDATE**: `uv run pytest tests/test_tools.py -q`
- **SATISFIES**: AC #3, #4

### UPDATE tests/test_e2e.py

- **IMPLEMENT**: add `"get_stress"` to the expected tool-name list.
- **VALIDATE**: `uv run pytest tests/test_e2e.py -q` (this single file only)
- **SATISFIES**: AC #5

### UPDATE docs and version

- **IMPLEMENT**:
  - `README.md`: change the `| Stress | No |` row to `| All-day stress | Yes (`get_stress`) |`, placed with the other "Yes" rows.
  - `AGENTS.md`: line 7 "ten tools: `ping` and nine Garmin tools" becomes eleven / ten, add "stress" to the list; line 29 add `get_stress` to the tool list.
  - `work/future-improvements.md`: change line 9 to `- Steps`.
  - Check `docs/` for tool counts or lists (`grep -rn "get_body_battery\|ten tools" docs`) and update any found, including "Last updated" dates and index entries per `docs/conventions/documentation.md`.
  - Version 0.5.0 to 0.6.0 in `pyproject.toml` and `src/my_garmin_mcp/__init__.py` (new tool = minor bump, as the body battery work did); then `uv lock`.
- **GOTCHA**: do not touch the work item's Outcome section in this lane; that is written at close.
- **VALIDATE**: `uv lock --check && uv run pytest tests/test_version.py -q`
- **SATISFIES**: AC #6

---

## TESTING STRATEGY

### Unit Tests

`tests/test_extract.py` for `stress_day` (pure, no I/O); framework is pytest, plain functions, no fixtures needed.

### Integration Tests

`tests/test_tools.py` (in-process MCP client over `FakeApi`) and `tests/test_e2e.py` (tool list). Run each file on its own.

### Edge Cases

- Day with no data (`{}`, `None`, empty `stressValuesArray`) is omitted and does not fail the call.
- Readings of -1/-2/null and non-numeric entries ignored; level 0 kept.
- Missing summary keys fall back to computed values; missing durations omitted.
- Local offset differing from GMT (e.g. +3h) shifts bucket times; ISO-string timestamps handled via `_epoch_ms`.
- Range longer than `MAX_DAYS_STRESS`, `end < start`, bad date format raise `InvalidRequest`.

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style

`uv run ruff check . && uv run ruff format --check .`

### Level 2: Unit Tests

`uv run pytest tests/test_extract.py tests/test_version.py tests/test_garmin_client.py tests/test_tools.py -q`

### Level 3: Integration Tests

`uv run pytest tests/test_e2e.py -q`

### Level 4: Manual Validation

Only with Garmin credentials in `.env`: `.claude/skills/local-dev-env/scripts/server.sh restart`, then call `get_stress` for yesterday through the Garmin-MCP-Local tools and compare the payload to the extractor's assumptions. Not required for completion.

### Level 5: Additional Validation (Optional)

`uv lock --check`. No type checker is configured.

---

## ACCEPTANCE CRITERIA

- [ ] `get_stress(start_date, end_date)` exists and returns per day: average and max stress, minutes in rest/low/medium/high where Garmin gives them, and `[local time, level]` readings in 30-minute buckets
- [ ] Extractor is pure, never raises on odd payloads, and drops days without data
- [ ] Range limited to `MAX_DAYS_STRESS` (7) with bounded parallelism via `per_day`; failures are `ToolError`s
- [ ] Unit tests for `stress_day` and tool tests cover the edge cases above
- [ ] End-to-end tool-list test includes `get_stress`
- [ ] README, AGENTS.md, `work/future-improvements.md` updated; version bumped in both places and `uv.lock` current
- [ ] `ruff check`, `ruff format --check` and the listed test files pass; no regressions

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully
- [ ] Unit tests pass, plus `tests/test_tools.py` and `tests/test_e2e.py`
- [ ] No linting errors
- [ ] Acceptance criteria all met

---

## OPEN QUESTIONS / ASSUMPTIONS

No gate questions: every open point is contained in this work item and cheap to change.

- Auto-decided — output fields: `date`, `avg_stress`, `max_stress`, `rest_min`, `low_min`, `medium_min`, `high_min`, `bucket_minutes`, `columns`, `readings` — contained to this tool, easy to adjust; mirrors the `get_heart_rate` field style. Task affected: `stress_day` (**GOTCHA** there).
- Auto-decided — sampling interval: fixed 30-minute buckets of mean level (Garmin samples about every 3 minutes, so about 48 rows/day) — contained, and the `bucket_minutes` argument of `stress_day` leaves room to expose it later like `get_heart_rate`.
- Auto-decided — range limit: 7 days (`MAX_DAYS_STRESS`), one request per day, about 48 rows each — reversible one-line constant.
- Auto-decided — durations reported in minutes, not seconds, for phone readability.
- Auto-decided — version bump 0.5.0 to 0.6.0 (minor, as for the previous new tool).
- Assumed — `Garmin.get_stress_data(day)` and the payload keys above match the locked `garminconnect` 0.3.17; confirm in the first task (library not installed while planning, no live data available).

## NOTES (open canvas)

- Alternative rejected: one summary-only tool with no readings. The work item asks for a downsampled series, and Body Battery/heart rate precedent shows the size is manageable.
- Alternative rejected: `[time, level]` per raw sample. About 480 pairs/day is too heavy for phone context.
- Bucket means smooth peaks; `max_stress` from Garmin's own summary preserves the peak value.

## AMENDMENTS

