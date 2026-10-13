# Implementation Plan: Add MCP tool: body battery

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Add a tenth tool (ninth Garmin tool), `get_body_battery`, to the my-garmin-mcp server. It returns Garmin Body Battery (0-100 energy level) per day for a date range as a compact per-day summary: highest, lowest, start-of-day and end-of-day level, charged and drained totals, plus a short downsampled series.

## User Story

As the owner asking Claude about my health data
I want Claude to read my Body Battery per day
So that it can reason about recovery and energy together with sleep, HRV and resting heart rate

## Problem Statement

Body Battery is listed as "not exposed" in the README coverage table (row "Stress, body battery") and in `work/future-improvements.md`. Claude cannot answer how drained or recharged I was on a given day.

## Solution Statement

Mirror the existing per-day tools (`get_heart_rate`, `get_resting_hr`). `garminconnect`'s `Garmin.get_body_battery(startdate, enddate=None)` takes a range and returns a **list** with one entry per day, so one Garmin request covers the whole range (unlike `per_day`, which does one request per day). The tool therefore calls `garmin.call(lambda g: g.get_body_battery(start, end))` once, and a new pure extractor `body_battery_days(payload)` reduces each entry. Days without readings are dropped, as in the other tools.

## Out of Scope / Non-Goals

- Not included: `get_body_battery_events` (charge/drain events such as sleep, activity, stress) — defer to a separate work item if wanted.
- Not included: stress data (`get_stress_data`) — separate item in `work/future-improvements.md`.
- Not included: a configurable bucket size parameter (a fixed downsample is used; add later only if needed).
- Not changing: `per_day` in `tools/_common.py`, `GarminClient`, auth, or other tools.

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: Low
**Primary Systems Affected**: `tools/`, `garmin/extract.py`, `garmin/dates.py`, tests, docs
**Dependencies**: `garminconnect>=0.3.17` (already in `pyproject.toml`); no new libraries

## Related Work

**Implements**: work item `HLB9Q-add-mcp-tool-body-battery` (`work/open/HLB9Q-add-mcp-tool-body-battery/HLB9Q-add-mcp-tool-body-battery.md`) · **Feature**: none (standalone work item)

**Back-references**:

- `work/implemented/2026-10-12-add-mcp-tool-all-day-heart-rate.md` - Why: same shape of work (new tool, extractor, tests, version bump, README row, AGENTS.md count). Its Outcome notes the Garmin payload shape was unverified against live data; the same applies here.

**Forward-references**:

- (none yet)

`Depends on: none` in the work item is correct; no hard dependency found.

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `src/my_garmin_mcp/tools/heart_rate.py` (whole file) - Why: closest tool to mirror (`register(server, garmin)`, `@server.tool(... annotations=ToolAnnotations(read_only_hint=True))`, `StartDate`/`EndDate`, `as_json` output shape `{start_date,end_date,count,<key>:[...]}`).
- `src/my_garmin_mcp/tools/_common.py` (whole file) - Why: `StartDate`, `EndDate`, `as_json`, and `per_day` (NOT usable here since body battery is one ranged request; reuse its `parse_range` call pattern).
- `src/my_garmin_mcp/garmin/dates.py` - Why: `parse_range(start, end, max_days)`, `InvalidRequest`, constants `MAX_DAYS_PER_DAY_TOOLS = 31`, `MAX_DAYS_HEART_RATE`.
- `src/my_garmin_mcp/garmin/extract.py` (`_clean` line 7, `resting_hr` ~75, `heart_rate_day` ~83-125) - Why: extractor style: pure, tolerant of missing/odd data (`isinstance` checks, `None` when empty), `_clean` drops `None` keys, rows as compact lists plus a `columns` key.
- `src/my_garmin_mcp/tools/__init__.py` - Why: add the module to the import and to the `for module in (...)` tuple.
- `tests/test_tools.py` (`FakeApi` ~lines 18-60; heart-rate tests ~135-150) - Why: add `get_body_battery` to `FakeApi`, mirror the heart-rate tool tests.
- `tests/test_extract.py` (heart-rate tests ~153-192) - Why: extractor unit-test style (parametrized empty payloads).
- `tests/test_e2e.py` (tool name list ~line 56-70) - Why: the expected sorted tool-name list must include `get_body_battery`.
- `README.md` (coverage table ~lines 15-45), `AGENTS.md` (lines 7 and 29), `work/future-improvements.md` (line 9), `docs/conventions/versioning.md` - Why: docs to update.

### New Files to Create

- `src/my_garmin_mcp/tools/body_battery.py` - the `get_body_battery` tool.

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- `garminconnect` source, `Garmin.get_body_battery` (https://github.com/cyberjunky/python-garminconnect, `garminconnect/__init__.py`; installed copy under `.venv` after `uv sync`)
  - Why: confirm the signature and response shape below. The library was not installed in the planning environment, so the shape here is from knowledge of the library, **unverified**. Check it first.

Expected shape (verify): `get_body_battery(startdate: str, enddate: str | None = None) -> list[dict]` calling `/wellness-service/wellness/bodyBattery/reports/daily`. Each entry roughly:

```json
{
  "date": "2026-10-12",
  "charged": 52, "drained": 41,
  "startTimestampGMT": "...", "endTimestampGMT": "...",
  "startTimestampLocal": "...", "endTimestampLocal": "...",
  "bodyBatteryValueDescriptorDTOList": [
    {"bodyBatteryValueDescriptorIndex": 0, "bodyBatteryValueDescriptorKey": "timestamp"},
    {"bodyBatteryValueDescriptorIndex": 1, "bodyBatteryValueDescriptorKey": "bodyBatteryStatus"},
    {"bodyBatteryValueDescriptorIndex": 2, "bodyBatteryValueDescriptorKey": "bodyBatteryLevel"},
    {"bodyBatteryValueDescriptorIndex": 3, "bodyBatteryValueDescriptorKey": "bodyBatteryVersion"}
  ],
  "bodyBatteryValuesArray": [[1760227200000, "MEASURED", 62, 2.0], ...]
}
```

### Patterns to Follow

**Naming**: tool `get_body_battery`, title "Body Battery", module `tools/body_battery.py`, extractor `body_battery_days`, JSON key `body_battery`.

**Error handling**: only `GarminError` (raised by `GarminClient.call`) and `InvalidRequest` (from `parse_range`) reach Claude with a useful message; any other exception becomes "Error executing tool". Extractors must therefore never raise on odd payloads.

**Output**: `as_json({"start_date": ..., "end_date": ..., "count": len(days), "body_battery": days})`.

**Per-day record** (use `_clean` to drop `None`): `date`, `highest`, `lowest`, `start`, `end`, `charged`, `drained`, `columns: ["time","level"]`, `readings` (downsampled).

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation

Confirm the `garminconnect` response shape; add the range constant and the extractor.

### Phase 2: Core Implementation

**Depends on:** Phase 1

The tool file calling `get_body_battery` once for the range.

### Phase 3: Integration

**Depends on:** Phase 2

Register in `tools/__init__.py`, bump the version, update docs.

### Phase 4: Testing & Validation

**Depends on:** Phases 1-3 (test files can be written alongside Phase 1/2)

Extractor unit tests, tool tests with `FakeApi`, e2e tool-list update.

---

## STEP-BY-STEP TASKS

### CHECK garminconnect `get_body_battery`

- **IMPLEMENT**: Run `uv sync`, then read `Garmin.get_body_battery` in the installed package (`uv run python -c "import garminconnect, inspect; print(inspect.getsource(garminconnect.Garmin.get_body_battery))"`). Confirm: takes `(startdate, enddate=None)`, one request, returns a list of per-day dicts; note the field names and the layout of `bodyBatteryValuesArray`. If the real shape differs from "Relevant Documentation" above, adapt the extractor to the real one and record it in the work item Outcome.
- **VALIDATE**: `uv run python -c "import garminconnect, inspect; print(inspect.signature(garminconnect.Garmin.get_body_battery))"`
- **SATISFIES**: AC #1

### UPDATE src/my_garmin_mcp/garmin/dates.py

- **ADD**: `MAX_DAYS_BODY_BATTERY = 31` (same value as `MAX_DAYS_PER_DAY_TOOLS`, with a comment: one request for the whole range, each day carries a time series). Place next to `MAX_DAYS_HEART_RATE`.
- **PATTERN**: `dates.py` constants block, lines 7-11.
- **GOTCHA**: Auto-decided limit (see Open Questions); if the real endpoint rejects 31 days, lower it.
- **VALIDATE**: `uv run ruff check src`
- **SATISFIES**: AC #2

### ADD body_battery_days to src/my_garmin_mcp/garmin/extract.py

- **IMPLEMENT**: `body_battery_days(payload: list[dict[str, Any]] | None) -> list[dict[str, Any]]`. For each entry that is a dict:
  - Locate the level column: from `bodyBatteryValueDescriptorDTOList` find the descriptor with key `bodyBatteryLevel` and use its `bodyBatteryValueDescriptorIndex`; fall back to index 2 if rows are 4 wide, else 1. Timestamp is column 0.
  - Skip rows that are not list/tuple, are too short, have a non-numeric timestamp or a non-numeric/`bool`/`None` level (copy the `isinstance(..., int | float)` and `bool` guard from `heart_rate_day`).
  - If no valid readings, skip the day (the day's `charged`/`drained` alone are not worth a record).
  - `highest`/`lowest` = max/min level; `start`/`end` = first/last valid level by timestamp order; `charged`/`drained` from entry (`None` dropped by `_clean`); `date` = `entry.get("date")`.
  - Downsample: bucket into 2-hour windows (local wall-clock) as `[HH:MM, level]` using the last level in each bucket. Local time via the offset between `startTimestampLocal` and `startTimestampGMT` **only if both are epoch numbers**; if they are ISO strings (shape unverified) parse them with `datetime.fromisoformat` or otherwise use offset 0, matching `heart_rate_day`'s "offset zero" fallback. Reuse `_local_iso`-style `datetime.fromtimestamp(..., UTC)`.
  - Return the list ordered by date.
- **PATTERN**: `heart_rate_day` in `extract.py` (~83-125) for tolerance and compact rows; `_clean` at line 7.
- **GOTCHA**: Accept a non-list payload (`None`, `{}`) and return `[]`. Never raise.
- **VALIDATE**: `uv run pytest tests/test_extract.py -q`
- **SATISFIES**: AC #1, #3, #4

### CREATE src/my_garmin_mcp/tools/body_battery.py

- **IMPLEMENT**: `register(server: MCPServer, garmin: GarminClient)` defining `get_body_battery(start_date: StartDate, end_date: EndDate) -> str` with `@server.tool(name="get_body_battery", title="Body Battery", description=..., annotations=ToolAnnotations(read_only_hint=True))`. Body: `start, end = parse_range(start_date, end_date, MAX_DAYS_BODY_BATTERY)`; `payload = await garmin.call(lambda g: g.get_body_battery(start.isoformat(), end.isoformat()))`; `days = body_battery_days(payload)`; return `as_json({...,"body_battery": days})`. Description: Body Battery (0-100) per day: highest, lowest, start, end, charged, drained, plus [local time, level] readings every 2 hours; at most 31 days per call; days without data are left out.
- **PATTERN**: `tools/heart_rate.py` and `tools/resting_hr.py`.
- **IMPORTS**: `from ..garmin.dates import MAX_DAYS_BODY_BATTERY, parse_range`; `from ..garmin.extract import body_battery_days`; `from ._common import EndDate, StartDate, as_json`.
- **GOTCHA**: Do not use `per_day` (it makes one request per day and passes a per-day payload). Call `parse_range` first so bad dates raise `InvalidRequest` before any Garmin call.
- **VALIDATE**: `uv run ruff check src && uv run ruff format --check src`
- **SATISFIES**: AC #1, #2

### UPDATE src/my_garmin_mcp/tools/__init__.py

- **ADD**: `body_battery` to the import line (keep alphabetical) and to the module tuple (after `heart_rate`/`resting_hr` grouping, e.g. `sleep, hrv, body_battery, heart_rate, ...`).
- **VALIDATE**: `uv run ruff check src`
- **SATISFIES**: AC #1

### UPDATE version (0.4.0 -> 0.5.0)

- **IMPLEMENT**: `version` in `pyproject.toml` and `__version__` in `src/my_garmin_mcp/__init__.py` to `0.5.0`; then `uv lock`.
- **PATTERN**: `docs/conventions/versioning.md`.
- **VALIDATE**: `uv lock --check && uv run pytest tests/test_version.py -q`
- **SATISFIES**: AC #6

### UPDATE tests/test_extract.py

- **ADD**: tests for `body_battery_days`: normal day (highest/lowest/start/end/charged/drained, 2-hour rows); descriptor-based level index (reorder the descriptor list); 2-wide rows fallback; null levels and malformed rows skipped; day with no readings omitted; `None`/`{}`/`[]` payloads give `[]`; multiple days keep order.
- **PATTERN**: heart-rate tests, `tests/test_extract.py` ~153-192 (including `pytest.mark.parametrize` for empties).
- **VALIDATE**: `uv run pytest tests/test_extract.py -q`
- **SATISFIES**: AC #3, #4

### UPDATE tests/test_tools.py

- **ADD**: `FakeApi.get_body_battery(self, start, end)` appending `f"bb {start} {end}"` to `self.calls` and returning two day entries (one empty `bodyBatteryValuesArray`). Tests: result has the expected days and drops the empty one; exactly **one** Garmin call for the range; a 32-day range and a bad date return `is_error`.
- **PATTERN**: `test_get_heart_rate_buckets_readings_and_skips_empty_days` (~135) and `..._rejects_bad_bucket_and_long_range` (~144).
- **VALIDATE**: `uv run pytest tests/test_tools.py -q`
- **SATISFIES**: AC #1, #2, #3

### UPDATE tests/test_e2e.py

- **ADD**: `"get_body_battery"` to the sorted tool-name list in `test_ping_with_valid_key` (~line 56).
- **VALIDATE**: `uv run pytest tests/test_e2e.py -q`
- **SATISFIES**: AC #1

### UPDATE docs

- **README.md**: change the row `| Stress, body battery | No |` to `| Stress | No |` and add `| Body battery | Yes (`get_body_battery`) |` among the "Yes" rows (after All-day heart rate).
- **AGENTS.md**: line 7 "nine tools: `ping` and eight Garmin tools" -> "ten tools: `ping` and nine Garmin tools", add "body battery" to the list; line 29 add `get_body_battery` to the tool list.
- **work/future-improvements.md** line 9: remove "body battery" (leaves "Stress (`get_stress_data`), steps").
- **docs/**: `grep -rn -i "heart_rate\|get_vo2max" docs` found no tool lists; re-grep to confirm none needs updating.
- **VALIDATE**: `grep -rn -i "body battery" README.md AGENTS.md work/future-improvements.md`
- **SATISFIES**: AC #5

---

## TESTING STRATEGY

pytest (+ pytest-asyncio style async tests already in `tests/test_tools.py`), fake Garmin API through `FakeApi`; e2e through the real MCP client in `tests/test_e2e.py`.

### Unit Tests

Extractor tests in `tests/test_extract.py` (see task). Pure functions, no I/O.

### Integration Tests

- `tests/test_tools.py` (tool through in-process MCP client with `FakeApi`) — run by file.
- `tests/test_e2e.py` (tool list) — run by file, only that file.

### Edge Cases

- Payload `None`, `{}`, `[]`, or entry with missing `bodyBatteryValuesArray`.
- Levels `None`, bool, string; rows shorter than the level column.
- Missing/reordered `bodyBatteryValueDescriptorDTOList`.
- Day with `charged`/`drained` but no readings (omitted).
- Range of 1 day, of 31 days (ok), of 32 days (`InvalidRequest`), `end < start`, malformed date.
- Garmin failure surfaces as `GarminError` (covered by `GarminClient` tests; no new code).

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style

`uv run ruff check . && uv run ruff format --check .`

### Level 2: Unit Tests

`uv run pytest tests/test_extract.py tests/test_version.py tests/test_garmin_client.py tests/test_tools.py -q`

### Level 3: Integration Tests

`uv run pytest tests/test_e2e.py -q`

### Level 4: Manual Validation

With real credentials only (none in the automated environment): `.claude/skills/local-dev-env/scripts/server.sh restart`, then call `get_body_battery` for the last 3 days via the Garmin-MCP-Local MCP tools and compare with the Garmin app. Not required for completion; state in the Outcome that live data was not checked if skipped.

### Level 5: Additional Validation (Optional)

None configured (no type checker in this project).

---

## ACCEPTANCE CRITERIA

- [ ] `get_body_battery(start_date, end_date)` is registered and returns compact JSON with per-day highest, lowest, start, end, charged, drained and a 2-hour downsampled series.
- [ ] Range limit is enforced (`MAX_DAYS_BODY_BATTERY`), and bad input raises `InvalidRequest`.
- [ ] Days with missing or malformed data are omitted and never raise.
- [ ] The extractor has unit tests; tool and e2e tests are extended.
- [ ] README coverage table, `AGENTS.md` and `work/future-improvements.md` are updated.
- [ ] Version is 0.5.0 in both places and `uv.lock` is current.
- [ ] `ruff check`, `ruff format --check` and the pytest files above pass.

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully
- [ ] Unit tests pass, and so do `tests/test_tools.py` and `tests/test_e2e.py`
- [ ] No linting errors
- [ ] Acceptance criteria all met

---

## OPEN QUESTIONS / ASSUMPTIONS

Nothing was gated: every open point is contained to this work item and cheap to change.

- Auto-decided — single date vs range: range (`start_date`/`end_date`, like the other tools), one Garmin request for the whole range since `get_body_battery` accepts a range — contained and reversible. Affects the tool task (do not use `per_day`).
- Auto-decided — range limit: 31 days (`MAX_DAYS_BODY_BATTERY`) — one request, and each day is summarised to ~12 rows, so output stays small; a constant, easy to lower. Affects the `dates.py` task (**GOTCHA**: real endpoint limit unverified).
- Auto-decided — fields: highest, lowest, start, end, charged, drained, plus a 2-hour series — the work item allowed a downsampled series; ~12 rows/day is small. Easy to drop.
- Auto-decided — `get_body_battery_events` excluded — optional in the work item; keeps the tool single-purpose.
- Auto-decided — version 0.5.0 (minor bump, as in the previous tool work).
- Assumed — the `garminconnect` response shape (see Documentation section) is from memory; the library was not installed here and there are no Garmin credentials. The first task verifies it against the installed source; live data stays unverified.

## NOTES (open canvas)

- Alternative rejected: reuse `per_day` with `get_body_battery(d)` for each day. It works but makes up to 31 requests (3 in parallel) where one suffices, and raises the risk of Garmin throttling.
- Alternative rejected: return the raw `bodyBatteryValuesArray` (about 100+ rows/day at ~3-minute resolution); too large for phone context.
- Downsampling uses the last level per 2-hour bucket (a level snapshot rather than an average), because Body Battery is a state, not a rate.

## AMENDMENTS

