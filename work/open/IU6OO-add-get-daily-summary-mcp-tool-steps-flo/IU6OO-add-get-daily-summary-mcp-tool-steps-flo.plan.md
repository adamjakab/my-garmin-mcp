# Implementation Plan: Add get_daily_summary MCP tool (steps, floors, intensity minutes)

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

A new MCP tool `get_daily_summary` returning, per day over a date range, Garmin's daily activity summary: steps and step goal, distance, floors climbed and floor goal, intensity minutes (moderate, vigorous, goal) and total/active calories. Compact JSON, days without data omitted, failures as `ToolError`s.

## User Story

As the owner asking Claude from the mobile app
I want to see my steps, floors and intensity minutes for a day or range
So that I can check activity and goal progress without opening Garmin Connect

## Problem Statement

No current tool exposes the basic daily movement numbers (README "Garmin coverage" lists "Daily summary, steps, floors" and "Intensity minutes" as `No`).

## Solution Statement

Add a per-day tool built on `GarminClient.call` + `per_day` (one `get_user_summary(date)` request per day, 3 at a time), a pure extractor `daily_summary_day` in `garmin/extract.py`, and a `MAX_DAYS_DAILY_SUMMARY` constant. Daily totals only (no intraday step buckets, no `get_steps_data`).

## Out of Scope / Non-Goals

- Not included: intraday step buckets / `get_steps_data` (defer to a separate work item).
- Not included: heart rate, stress, body battery fields that `get_user_summary` also carries (other tools cover them).
- Not changing: existing tools, `per_day`, `GarminClient`, `stress_day` or other extractors.

## Feature Metadata

**Feature Type**: New Capability (Enhancement)
**Estimated Complexity**: Low
**Primary Systems Affected**: `tools/`, `garmin/extract.py`, `garmin/dates.py`, tests, docs
**Dependencies**: `garminconnect` (`Garmin.get_user_summary(cdate)`), already installed

## Related Work

**Implements**: work item `IU6OO-add-get-daily-summary-mcp-tool-steps-flo` (`work/open/IU6OO-add-get-daily-summary-mcp-tool-steps-flo/IU6OO-add-get-daily-summary-mcp-tool-steps-flo.md`) · **Feature**: none (standalone item, nothing to inherit). `Depends on: none` is correct; no hard dependency found.

**Back-references**:

- `work/implemented/2026-10-16-add-spo2-and-respiration-mcp-tool-s.md` - Why: the most recent per-day tool pair; same file layout, tests, version bump and doc edits.

**Forward-references**:

- (none yet)

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `src/my_garmin_mcp/tools/spo2.py` (all) - Why: the template for a per-day tool (`@server.tool` name/title/description/annotations, `per_day`, `as_json` envelope).
- `src/my_garmin_mcp/tools/_common.py` (lines 15-24, 27-29) - Why: `per_day(garmin, start, end, max_days, fetch, extract)` and `as_json`; `StartDate`/`EndDate`.
- `src/my_garmin_mcp/tools/__init__.py` - Why: add the module to the import list and the `for module in (...)` tuple.
- `src/my_garmin_mcp/garmin/dates.py` (lines 7-15) - Why: where `MAX_DAYS_*` constants live; `MAX_DAYS_PER_DAY_TOOLS = 31`.
- `src/my_garmin_mcp/garmin/extract.py` (lines 7-9 `_clean`, 75-80 `resting_hr`, 417-420 `_in_range`, 454-483 `spo2_day`, 524-557 training readiness helpers `_tr_number`) - Why: helper reuse and the "odd payloads never raise" style.
- `tests/test_extract.py` (lines 1-16 imports, 451-515 spo2 tests) - Why: extractor test style, parametrized empty payloads.
- `tests/test_tools.py` (`FakeApi` lines 17-90, spo2 tests ~298-317) - Why: add `get_user_summary` to `FakeApi` and mirror the three tool tests.
- `tests/test_e2e.py` (lines 60-76) - Why: tool-name list to extend.
- `tests/test_version.py`, `pyproject.toml:3`, `src/my_garmin_mcp/__init__.py:2` - Why: version bump (0.8.0 -> 0.9.0).
- `README.md` (Garmin coverage table, lines ~38 and ~41), `AGENTS.md` (lines 7, 29), `work/future-improvements.md` (lines 9-10), `docs/conventions/documentation.md` - Why: docs to update.

### New Files to Create

- `src/my_garmin_mcp/tools/daily_summary.py` - the tool.

### Relevant Documentation

- garminconnect `Garmin.get_user_summary(cdate)` (GET `usersummary-service/usersummary/daily/<displayName>?calendarDate=`). Source: https://github.com/cyberjunky/python-garminconnect (`garminconnect/__init__.py`, search `def get_user_summary`).
  - Why: payload keys. The library is not installed in the planning checkout, so keys below come from the known payload and are **unverified**; the implementer should check `.venv` after `uv sync` (`grep -n "def get_user_summary" -A20 .venv/lib/python3.12/site-packages/garminconnect/__init__.py`) and tolerate missing keys.

### Patterns to Follow

**Naming**: tool `get_daily_summary`, extractor `daily_summary_day`, constant `MAX_DAYS_DAILY_SUMMARY`, response envelope key `"days"`? Mirror siblings: key is the domain name, so use `"daily_summary"`: `{"start_date", "end_date", "count", "daily_summary": [...]}`.

**Error handling**: no try/except in the tool; `GarminError`/`InvalidRequest` arise in `garmin.call`/`parse_range`. Extractor never raises on odd payloads (`isinstance(payload, dict)` guard, return None).

**Extractor shape** (mirror `spo2_day`): validate numbers, build dict with `"date": payload.get("calendarDate") or day`, pass through `_clean` (drops None). Return None when no useful value is present.

Assumed payload keys (snake_case output in parentheses):
`totalSteps` (steps), `dailyStepGoal` (step_goal), `totalDistanceMeters` (distance_m), `userFloorsAscendedGoal` (floors_goal), `floorsAscended` (floors_climbed, round to int), `moderateIntensityMinutes` (moderate_intensity_min), `vigorousIntensityMinutes` (vigorous_intensity_min), `intensityMinutesGoal` (intensity_goal_min), `totalKilocalories` (calories), `activeKilocalories` (active_calories).
Day-has-data rule: a day with no `totalSteps`, no distance and no floors/intensity/calories values (all None) -> None. A day where `totalSteps` is 0 but the payload exists is still real data (keep 0) only if some other value is non-null; goal-only payloads (device not worn) should be dropped, so decide on the activity fields (steps, distance, floors, intensity minutes, calories) only, not goals.

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation
Add `MAX_DAYS_DAILY_SUMMARY` and the pure extractor.

### Phase 2: Core Implementation
**Depends on:** Phase 1. Create the tool file.

### Phase 3: Integration
Register in `tools/__init__.py`; bump version; update docs.

### Phase 4: Testing & Validation
**Independent of:** Phase 3 docs (tests need Phase 1-2 only). Extractor unit tests, FakeApi + tool tests, e2e list.

---

## STEP-BY-STEP TASKS

### UPDATE src/my_garmin_mcp/garmin/dates.py
- **IMPLEMENT**: `MAX_DAYS_DAILY_SUMMARY = MAX_DAYS_PER_DAY_TOOLS  # small payload per day, one request per day` (or the literal 31).
- **PATTERN**: dates.py:7-14.
- **GOTCHA**: Auto-decided limit 31: each day is ~12 small numbers, so no time series to justify 7.
- **VALIDATE**: `uv run ruff check src`
- **SATISFIES**: range limit as `MAX_DAYS_*`.

### ADD daily_summary_day to src/my_garmin_mcp/garmin/extract.py
- **IMPLEMENT**: `def daily_summary_day(day: str, payload: dict[str, Any] | None) -> dict[str, Any] | None` per the key mapping above. Use `_in_range(value, 0, <sane max>)` or `_tr_number`-style helper to reject bools/non-numbers/negatives (check `_in_range`, extract.py:417, accepts what you need). Floors may be floats (e.g. 12.0): output `round()`ed ints. Put after `respiration_day`/training readiness at file end.
- **PATTERN**: `spo2_day` extract.py:454-483.
- **GOTCHA**: Unverified payload keys (see docs section); every key optional. `_clean` drops None only, so zero values stay.
- **VALIDATE**: `uv run pytest tests/test_extract.py -q`
- **SATISFIES**: compact output, empty days omitted.

### CREATE src/my_garmin_mcp/tools/daily_summary.py
- **IMPLEMENT**: `register(server, garmin)`; tool `get_daily_summary`, title "Daily summary (steps, floors, intensity minutes)", description listing fields, "At most {MAX_DAYS_DAILY_SUMMARY} days per call; days without data are left out."; fetch `lambda g, d: g.get_user_summary(d)`, extract `daily_summary_day`; return `as_json({"start_date", "end_date", "count", "daily_summary": days})`.
- **PATTERN**: tools/spo2.py.
- **VALIDATE**: `uv run ruff check src`
- **SATISFIES**: tool exists, uses `per_day`.

### UPDATE src/my_garmin_mcp/tools/__init__.py
- **IMPLEMENT**: import `daily_summary` (alphabetical, after `body_battery`) and add to the module tuple (after `weight`/before `activities` or beside stats tools).
- **VALIDATE**: `uv run python -c "import my_garmin_mcp.tools"`

### UPDATE tests/test_extract.py
- **IMPLEMENT**: import `daily_summary_day`; tests: full payload maps all fields; floats rounded; missing keys tolerated; goal-only payload -> None; parametrized empties (`None`, `{}`, `[]`, `"x"`, all-null) -> None; bool/negative/string values ignored; date falls back to `day`.
- **PATTERN**: test_extract.py:451-515.
- **VALIDATE**: `uv run pytest tests/test_extract.py -q`

### UPDATE tests/test_tools.py
- **IMPLEMENT**: `FakeApi.get_user_summary(self, day)` recording `f"summary {day}"`, returning `{}`/no-activity payload for `-02` and a full payload otherwise; add the three tests (returns days & skips empty, one request per day, rejects 32-day range and bad date).
- **PATTERN**: tests/test_tools.py:52-61, 298-317.
- **VALIDATE**: `uv run pytest tests/test_tools.py -q`

### UPDATE tests/test_e2e.py
- **IMPLEMENT**: add `"get_daily_summary"` to the expected tool list (line ~63-76).
- **VALIDATE**: `uv run pytest tests/test_e2e.py -q`

### UPDATE version
- **IMPLEMENT**: 0.8.0 -> 0.9.0 in `pyproject.toml` and `src/my_garmin_mcp/__init__.py`, then `uv lock`.
- **VALIDATE**: `uv run pytest tests/test_version.py -q && uv lock --check`

### UPDATE docs
- **IMPLEMENT**: README table: "Daily summary, steps, floors" and "Intensity minutes" -> `Yes (\`get_daily_summary\`)` (merge into one row if cleaner). AGENTS.md line 7: "fifteen tools: `ping` and fourteen Garmin tools (..., daily summary, ...)" and line 29 tool list. Remove "Steps" and "floors, intensity minutes" from `work/future-improvements.md:9-10` (keep "Training status, hydration"). Check `docs/architecture/overview.md` lists no tools (per prior item it does not).
- **VALIDATE**: `grep -n "get_daily_summary" README.md AGENTS.md`

---

## TESTING STRATEGY

### Unit Tests
Extractor tests in `tests/test_extract.py` as above (pure functions, no mocks).

### Integration Tests
`tests/test_tools.py` (in-memory MCP client with `FakeApi`) and `tests/test_e2e.py` (tool list). Run each file by name.

### Edge Cases
No-data day dropped; goal-only payload dropped; zero steps with other activity data kept; non-dict payload; bool/negative/str numbers; float floors; 31 days OK, 32 rejected; bad date string.

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style
`uv run ruff check src tests && uv run ruff format --check src tests`

### Level 2: Unit Tests
`uv run pytest tests/test_extract.py tests/test_version.py -q`

### Level 3: Integration Tests
`uv run pytest tests/test_tools.py -q` and `uv run pytest tests/test_e2e.py -q`

### Level 4: Manual Validation
Needs real credentials; if available, start via the `local-dev-env` skill and call `get_daily_summary` for one recent day to confirm the real payload keys match the mapping (adjust the extractor if not). Otherwise state it was not run.

---

## ACCEPTANCE CRITERIA

- [ ] `get_daily_summary(start_date, end_date)` returns per-day steps, step goal, distance, floors and floor goal, intensity minutes and goal, calories as compact JSON
- [ ] Days without data are omitted; range over `MAX_DAYS_DAILY_SUMMARY` and bad dates give `InvalidRequest`
- [ ] One request per day through `per_day`
- [ ] Extractor unit tests, tool tests and the e2e tool list updated and passing
- [ ] Version 0.9.0 in `pyproject.toml`, `__version__`, `uv.lock`
- [ ] README, AGENTS.md, `work/future-improvements.md` updated
- [ ] ruff check and format pass

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed
- [ ] Lint clean
- [ ] Tests for the changed files pass
- [ ] Acceptance criteria met

---

## OPEN QUESTIONS / ASSUMPTIONS

Gate: nothing survived triage; the one open question in the work item is settled by its stated default.

- Auto-decided — intraday step buckets vs daily totals: daily totals only, per the work item's default — adding buckets later is additive and does not change this tool's contract.
- Auto-decided — range limit: 31 days (`MAX_DAYS_DAILY_SUMMARY`) — small payload; constant is trivially changed.
- Auto-decided — response envelope key `daily_summary` and snake_case field names — mirrors `spo2`/`respiration`; contained to this tool.
- Auto-decided — include calories (`calories`, `active_calories`), allowed by the work item's "where compact"; leave out descended floors to stay compact.
- Assumed — `get_user_summary` payload keys listed above (library not installed in the planning checkout), confirm against the installed library or a real call before relying on them. Tasks "ADD daily_summary_day" carries this GOTCHA.

## NOTES (open canvas)

- `get_stats` is an alias-style sibling of `get_user_summary` in some library versions; `get_user_summary` is what the work item names, so use it. If the installed version lacks it, fall back to `get_stats(date)` (same payload) and note it in the outcome.
- Rejected: `get_steps_data` per-day buckets (long series, phone context cost).

## AMENDMENTS

- (none)
