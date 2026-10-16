# Implementation Plan: Add get_training_readiness MCP tool

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

A twelfth MCP tool, `get_training_readiness`, returning Garmin's Training Readiness per day for a date range: the score (0-100), the level (e.g. `PRIME`, `HIGH`, `MODERATE`, `LOW`, `POOR`), Garmin's short feedback, and the contributing factors (sleep, recovery time, acute/chronic load ratio, HRV, stress history), each with a percent and a feedback key. Backed by `Garmin.get_training_readiness(cdate)` via the shared `GarminClient`.

## User Story

As the owner asking Claude from the mobile app
I want to see my Garmin Training Readiness and what drives it
So that I can decide whether to train hard today.

## Problem Statement

Training readiness is listed under "Ideas for later" in `work/future-improvements.md:10` and is not reachable from Claude. It complements `get_sleep`, `get_hrv`, `get_body_battery`.

## Solution Statement

Mirror `get_stress`: a thin tool `tools/training_readiness.py` using `per_day` (one request per day), with a pure, unit-tested `training_readiness_day` in `garmin/extract.py` that picks one snapshot per day and keeps a compact set of fields. A range-limit constant goes in `garmin/dates.py`.

## Out of Scope / Non-Goals

- Not included: training status, four-week load balance, endurance/hill score (defer to separate work items; training status is a separate bullet in `work/future-improvements.md`).
- Not included: returning every snapshot of a day (only the chosen one).
- Not changing: `GarminClient`, auth, existing tools' output.
- Not changing: `get_morning_training_readiness` is not used (see Notes).

## Feature Metadata

**Feature Type**: New Capability (Enhancement)
**Estimated Complexity**: Low
**Primary Systems Affected**: `tools/`, `garmin/extract.py`, `garmin/dates.py`, docs, tests
**Dependencies**: `garminconnect>=0.3.17` (already installed; no new dependency)

## Related Work

**Implements**: work item `R367F-add-get-training-readiness-mcp-tool` (`work/open/R367F-add-get-training-readiness-mcp-tool/R367F-add-get-training-readiness-mcp-tool.md`) · **Feature**: none (standalone item; `Depends on: none` verified, no hard dependency found)

**Back-references**:

- `work/implemented/2026-10-16-add-get-stress-mcp-tool-for-all-day-stre.md` - Why: same per-day tool pattern, same doc/version/e2e checklist

**Forward-references**:

- (none yet)

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `src/my_garmin_mcp/tools/stress.py` (whole file) - Why: exact template for the tool (decorator, `per_day`, `as_json` envelope)
- `src/my_garmin_mcp/tools/_common.py` (lines 8-30) - Why: `StartDate`, `EndDate`, `per_day`, `as_json`
- `src/my_garmin_mcp/tools/__init__.py` (whole) - Why: import list and the `for module in (...)` tuple to extend
- `src/my_garmin_mcp/garmin/dates.py` (lines 8-15) - Why: where `MAX_DAYS_*` constants live; `parse_range`, `InvalidRequest`
- `src/my_garmin_mcp/garmin/extract.py` (lines 1-16, 338-413) - Why: `_clean`, `_epoch_ms`, `_stress_level` style; `stress_day` shows "never raise on odd payloads, None when empty"
- `tests/test_extract.py` (lines 1-15 imports, 301-370) - Why: extract test style
- `tests/test_tools.py` (lines 15-60 `FakeApi`, 208-228 stress tests) - Why: fake API + tool test style
- `tests/test_e2e.py` (lines 60-75) - Why: sorted tool-name list to extend
- `README.md` (lines 15-40) - Why: tool table (add row, leave "Training readiness" absent from the "No" rows)
- `AGENTS.md` (lines 7 and 29) - Why: tool count ("eleven tools", "ten Garmin tools") and tool list
- `docs/conventions/versioning.md`, `docs/conventions/documentation.md` - Why: bump and doc rules
- `.venv/lib/python3.13/site-packages/garminconnect/__init__.py` (2290-2296) and `typed.py` (319-380) - Why: verified method signature and payload field names (run `uv sync` if `.venv` is missing)

### New Files to Create

- `src/my_garmin_mcp/tools/training_readiness.py`

### Relevant Documentation

- The installed `garminconnect/typed.py` `TrainingReadiness` model is the field reference (no network needed).
  - `get_training_readiness(cdate: str) -> list[dict]`: a **list of snapshots** per day (wake-up event or scheduled update); newest by `timestamp`. Payload keys (camelCase): `calendarDate, timestamp, timestampLocal, score, level, feedbackLong, feedbackShort, sleepScore, sleepScoreFactorPercent, sleepScoreFactorFeedback, recoveryTime (minutes), recoveryTimeFactorPercent, recoveryTimeFactorFeedback, recoveryTimeChangePhrase, acwrFactorPercent, acwrFactorFeedback, hrvFactorPercent, hrvFactorFeedback, stressHistoryFactorPercent, stressHistoryFactorFeedback, inputContext` (e.g. `AFTER_WAKEUP_RESET`). The typed docstring notes the library may also hand back a single dict, and an empty list/None for no data.

### Patterns to Follow

**Tool** (`tools/stress.py`): `register(server, garmin)`, `@server.tool(name=..., title=..., description=..., annotations=ToolAnnotations(read_only_hint=True))`, returns `as_json({"start_date", "end_date", "count", "<key>": days})`. Description states fields and "At most N days per call; days without data are left out."

**Extract**: pure `(day, payload) -> dict | None`; `isinstance` guards, never raise; `_clean()` drops `None`; `date` = `payload.get("calendarDate") or day`.

**Errors**: only `GarminError` / `InvalidRequest` (`ToolError`) reach Claude; `per_day` -> `parse_range` handles bad dates and long ranges.

**Compact output**: short snake_case keys (`avg_stress`, `rest_min` style).

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation
Range constant and the pure extractor.

### Phase 2: Core Implementation
**Depends on:** Phase 1. The tool file.

### Phase 3: Integration
Register in `tools/__init__.py`; docs; version bump.

### Phase 4: Testing & Validation
**Independent of:** Phase 3 docs (tests need Phase 1-3 code registration).

---

## STEP-BY-STEP TASKS

### UPDATE src/my_garmin_mcp/garmin/dates.py

- **IMPLEMENT**: ADD `MAX_DAYS_TRAINING_READINESS = 31  # one small request per day` next to the other `MAX_DAYS_*` constants.
- **PATTERN**: `dates.py:8-14`
- **GOTCHA**: Auto-decided limit 31 = `MAX_DAYS_PER_DAY_TOOLS`, since payload per day is small (no time series) and concurrency is already capped at 3 by `map_days`. Could reuse `MAX_DAYS_PER_DAY_TOOLS` directly instead; either is fine, but check which other per-day tools (sleep/hrv) use and mirror it.
- **VALIDATE**: `uv run ruff check src`
- **SATISFIES**: AC #1

### ADD training_readiness_day to src/my_garmin_mcp/garmin/extract.py

- **IMPLEMENT**: `def training_readiness_day(day: str, payload: list[dict] | dict | None) -> dict | None`.
  1. Normalise: dict -> `[payload]`; list -> keep only dict items; anything else/empty -> `None`.
  2. Choose snapshot: the one with the greatest `timestamp` (ISO string compare is fine; entries without a timestamp sort lowest; ties keep the later list item). Rationale: the typed docstring says to use the most recent for the current reading.
  3. Return `_clean({...})` with keys: `date` (`calendarDate` or `day`), `score`, `level`, `feedback` (`feedbackShort`), `time` (local `HH:MM` from `timestampLocal`, if parseable; skip otherwise), `recovery_h` is NOT used: keep `recovery_min` (`recoveryTime`, minutes, as Garmin gives) and `recovery_phase` (`recoveryTimeChangePhrase`), plus `factors`: a dict keyed `sleep`, `recovery`, `load` (acwr), `hrv`, `stress`, each `{"pct": <FactorPercent>, "feedback": <FactorFeedback>}` cleaned, omitted when both are None; and `sleep_score` (`sleepScore`).
  4. Return `None` when there is neither a numeric `score` nor a `level` (empty day).
  5. Validate types: score must be an int/float non-bool; strings must be `str`; otherwise treated as None. Drop `feedbackLong` (too bulky).
- **PATTERN**: `extract.py:338-413` (`stress_day`), helper `_clean` at `extract.py:7`
- **GOTCHA**: `timestampLocal` format is not confirmed by a live payload; parse defensively (`datetime.fromisoformat` in try/except, also accept epoch ms via `_epoch_ms`) and omit `time` on failure. The `score` may be 0, so test `is not None`, never truthiness.
- **VALIDATE**: `uv run pytest tests/test_extract.py -k training_readiness -q`
- **SATISFIES**: AC #2, #3

### CREATE src/my_garmin_mcp/tools/training_readiness.py

- **IMPLEMENT**: copy `tools/stress.py`; name `get_training_readiness`, title `"Training readiness"`, description: "Garmin Training Readiness per day: score (0-100), level, short feedback, local time of the reading and the contributing factors (sleep, recovery, load, HRV, stress) as percent and feedback; if there are several readings in a day the latest is used. At most {MAX_DAYS_TRAINING_READINESS} days per call; days without data are left out." Fetch lambda `lambda g, d: g.get_training_readiness(d)`; envelope key `"training_readiness"`.
- **PATTERN**: `tools/stress.py:1-35`
- **IMPORTS**: `MAX_DAYS_TRAINING_READINESS` from `..garmin.dates`, `training_readiness_day` from `..garmin.extract`, `EndDate, StartDate, as_json, per_day` from `._common`
- **VALIDATE**: `uv run ruff check src && uv run ruff format --check src`
- **SATISFIES**: AC #1

### UPDATE src/my_garmin_mcp/tools/__init__.py

- **IMPLEMENT**: import `training_readiness` (keep the alphabetical import line; ruff isort will wrap if > line length, run `ruff format`) and add it to the `for module in (...)` tuple after `stress`.
- **VALIDATE**: `uv run ruff check src && uv run python -c "import my_garmin_mcp.tools"`
- **SATISFIES**: AC #1

### UPDATE tests

- **tests/test_extract.py**: import `training_readiness_day`; tests: picks latest snapshot by `timestamp`; accepts a single dict; maps factors and drops `None` factors; score `0` kept; returns `None` for `None`, `[]`, `{}`, non-dict, and for snapshots with no score and no level; odd types (bool score, string percent) never raise; bad/missing `timestampLocal` omits `time`.
- **tests/test_tools.py**: ADD `get_training_readiness(self, day)` to `FakeApi` (record `self.calls.append(f"tr {day}")`; return `[]` for days ending `-02`, else a list with two snapshots). Tests mirroring lines 208-228: returns days and skips empty ones, one request per day, rejects range > `MAX_DAYS_TRAINING_READINESS` (use a >31 day range) and bad date.
- **tests/test_e2e.py**: add `"get_training_readiness"` to the expected tool list (the test sorts both sides).
- **VALIDATE**: `uv run pytest tests/test_extract.py tests/test_tools.py tests/test_e2e.py -q`
- **SATISFIES**: AC #2, #3, #4

### UPDATE docs and version

- `README.md`: add row `| Training readiness | Yes (`get_training_readiness`) |` after "All-day stress".
- `AGENTS.md`: line 7 "eleven tools" -> "twelve tools", "ten Garmin tools" -> "eleven Garmin tools", add "training readiness" to the list; line 29 add `get_training_readiness` to the tool names.
- `work/future-improvements.md:10`: rewrite the bullet to drop "Training readiness" and keep "training status, SpO2, ...".
- Check `docs/architecture/overview.md` and `docs/setup/local.md` for tool counts or lists (`grep -rn -i "eleven\|get_stress" docs README.md`) and update any found.
- Version: bump 0.6.0 -> 0.7.0 in `pyproject.toml` and `src/my_garmin_mcp/__init__.py`, then `uv lock`.
- Per `docs/conventions/documentation.md`, update any "Last updated" date on docs you edit.
- **VALIDATE**: `uv lock --check && uv run pytest tests/test_version.py -q`
- **SATISFIES**: AC #5

---

## TESTING STRATEGY

Pytest with the existing fakes; no live Garmin access.

### Unit Tests
`tests/test_extract.py` for `training_readiness_day`.

### Integration Tests
`tests/test_tools.py` (in-process MCP client with `FakeApi`) and `tests/test_e2e.py` (tool list only; it is the existing end-to-end file and is changed by one line, run by file).

### Edge Cases
Empty list / `None` / dict instead of list; multiple snapshots; score 0; missing factor fields; non-numeric values; missing/unparseable `timestampLocal`; range of 32 days; end before start; bad date.

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style
`uv run ruff check . && uv run ruff format --check .`

### Level 2: Unit Tests
`uv run pytest tests/test_extract.py tests/test_tools.py tests/test_version.py -q`

### Level 3: Integration Tests
`uv run pytest tests/test_e2e.py -q`

### Level 4: Manual Validation
Not possible without Garmin credentials. If available: `.claude/skills/local-dev-env/scripts/server.sh restart`, then call `get_training_readiness` for today and check the output against the Garmin app; record "not run" in the Outcome otherwise.

---

## ACCEPTANCE CRITERIA

- [ ] `get_training_readiness(start_date, end_date)` is registered, read-only, and returns compact JSON `{start_date,end_date,count,training_readiness:[...]}`
- [ ] Per day: score, level, feedback, factors (sleep/recovery/load/hrv/stress) with pct+feedback; the latest snapshot is chosen; empty days are omitted
- [ ] Bad dates / ranges over the limit raise `InvalidRequest`; Garmin failures surface as `GarminError`
- [ ] New unit, tool and e2e tests pass; `ruff` clean
- [ ] README, AGENTS.md, future-improvements updated; version bumped in both places and `uv.lock` current

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed
- [ ] All validation commands executed successfully
- [ ] No linting errors
- [ ] Acceptance criteria all met

---

## OPEN QUESTIONS / ASSUMPTIONS

No gate questions: nothing here ripples beyond this work item.

- Auto-decided — which library method: `Garmin.get_training_readiness(cdate)` (the "expected" one; verified in the installed library) — returns every snapshot of the day, so it is more faithful than `get_morning_training_readiness`; contained and reversible.
- Auto-decided — which snapshot per day: latest by `timestamp` (the library docs call this the current reading) rather than the morning one — a one-line change in the extractor if the owner prefers the morning reading.
- Auto-decided — fields kept: score, level, short feedback, local time, recovery minutes/phase, sleep score and the five factors; `feedbackLong`, device/profile ids dropped for phone compactness.
- Auto-decided — range limit 31 days, one request per day via `per_day`.
- Auto-decided — version bump is minor (0.7.0), as with previous new tools.
- Assumed — the real payload matches `typed.TrainingReadiness`; no live payload was available, so the extractor is defensive and `timestampLocal` parsing is best effort. Confirm with a live call after deploy.

## NOTES (open canvas)

- Alternative rejected: return all snapshots per day. More data on a phone, little value.
- Alternative rejected: `get_morning_training_readiness` — falls back to the first entry when no `AFTER_WAKEUP_RESET`, so the chosen snapshot is less predictable.
- `Depends on: none` in the work item stays correct.

## AMENDMENTS

