# Implementation Plan: Add SpO2 and respiration MCP tool(s)

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Expose two new per-day Garmin tools, `get_spo2` (blood oxygen) and `get_respiration` (breathing rate), from the my-garmin-mcp server. Each returns per day a summary plus a downsampled `[local time, value]` series, as compact JSON, built on `Garmin.get_spo2_data(day)` and `Garmin.get_respiration_data(day)` from `garminconnect` (locked 0.3.17).

## User Story

As the owner using Claude on the phone
I want to ask about my blood oxygen and breathing rate over a range of days
So that I can see overnight/recovery trends next to sleep, HRV, resting HR and stress

## Problem Statement

SpO2 and respiration are listed as "Not yet" in `README.md` (line 39) and in `work/future-improvements.md` (line 10). Only sleep summaries carry a night's avg/lowest SpO2 and avg respiration (`sleep_summary`, `garmin/extract.py:48-50`).

## Solution Statement

Two tools, one file each, mirroring `get_stress` exactly: `per_day(...)` fetch (one request per day), pure extractor in `garmin/extract.py` (`spo2_day`, `respiration_day`), a range constant per tool in `garmin/dates.py`. Two tools rather than one combined: the endpoints are separate (a combined tool would double the requests per day and the payload for callers who want one signal), the payloads differ, and every existing tool is one signal per tool.

## Out of Scope / Non-Goals

- Not included: a combined `get_spo2_respiration` tool.
- Not included: pulse-ox acclimatization, sleep-stage breakdowns or any other field from these payloads beyond what is listed under the tasks.
- Not included: hydration, floors, intensity minutes, training status (stay in `work/future-improvements.md`).
- Not changing: `get_sleep` output, `GarminClient`, auth, `per_day`/`map_days`, existing range limits.

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: Low-Medium (mirrors an existing tool twice; the risk is the unverified payload shape)
**Primary Systems Affected**: `tools/`, `garmin/extract.py`, `garmin/dates.py`, tests, docs
**Dependencies**: `garminconnect` (already installed, 0.3.17); no new libraries

## Related Work

**Implements**: work item `6F8JA-add-spo2-and-respiration-mcp-tool-s` (`work/open/6F8JA-add-spo2-and-respiration-mcp-tool-s/6F8JA-add-spo2-and-respiration-mcp-tool-s.md`) · **Feature**: none (standalone work item)

**Back-references**:

- `work/implemented/2026-10-16-add-get-stress-mcp-tool-for-all-day-stre.md` - Why: same shape (per-day request, time series, 30-minute buckets, `MAX_DAYS_STRESS`), including its documented deviation (omit series fields when a day has a summary but no readings)
- `work/implemented/2026-10-16-add-get-training-readiness-mcp-tool.md` - Why: latest example of the version bump + doc update checklist

**Forward-references**:

- (none yet)

`Depends on: none` on the work item is correct; no other open item touches these files.

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `src/my_garmin_mcp/tools/stress.py` (all) - Why: the exact template for a per-day tool (`register(server, garmin)`, `per_day`, `as_json`, output envelope)
- `src/my_garmin_mcp/tools/_common.py` (all) - Why: `per_day`, `StartDate`, `EndDate`, `as_json`
- `src/my_garmin_mcp/tools/__init__.py` (all) - Why: module import list and the registration tuple to extend
- `src/my_garmin_mcp/garmin/dates.py` (lines 7-14) - Why: range constants; add new ones here
- `src/my_garmin_mcp/garmin/extract.py` (lines 1-16, 128-141, 338-414) - Why: `_clean`, `_epoch_ms` (handles ms and ISO timestamps), `_stress_level`/`stress_day` (offset local-GMT, bucketing, defensive typing: never raise)
- `tests/test_extract.py` (lines 302-390) - Why: extractor test pattern (summary, offset, ISO timestamps, invalid rows, summary-only, parametrized empty payloads)
- `tests/test_tools.py` (lines 30-60, 224-245) - Why: fake Garmin API class (`get_stress_data`) and tool tests (empty days skipped, one request per day, long range rejected)
- `tests/test_e2e.py` (lines 60-80) - Why: the sorted tool-name list to extend
- `tests/test_version.py` - Why: version consistency check
- `README.md` (lines 20-40 and the Documentation section), `AGENTS.md` (Project status paragraph and Architecture tool list), `docs/architecture/overview.md`, `.claude/skills/local-dev-env/SKILL.md` - Why: tool lists/counts to update (grep for `get_stress` and "twelve"/"eleven")
- `docs/conventions/documentation.md`, `docs/conventions/versioning.md` - Why: doc and version rules

### New Files to Create

- `src/my_garmin_mcp/tools/spo2.py` - `get_spo2`
- `src/my_garmin_mcp/tools/respiration.py` - `get_respiration`

### Relevant Documentation

- garminconnect source for the installed version (`uv sync`, then read `.venv/lib/python3.*/site-packages/garminconnect/__init__.py`, search `def get_spo2_data` and `def get_respiration_data`)
  - Why: confirm method names and signature (`cdate: str`, YYYY-MM-DD) before coding. The library was not installed in the planning checkout, so the payload shapes below come from the known Garmin endpoints and are **unverified**.

### Patterns to Follow

**Tool shape** (from `tools/stress.py`):
```python
days = await per_day(garmin, start_date, end_date, MAX_DAYS_STRESS,
                     lambda g, d: g.get_stress_data(d), stress_day)
return as_json({"start_date": start_date, "end_date": end_date, "count": len(days), "stress": days})
```
New outputs use the keys `spo2` and `respiration` for the list.

**Error handling:** tools raise nothing themselves; `parse_range` raises `InvalidRequest`, `GarminClient.call` raises `GarminError`. Extractors return `None` for empty/odd payloads and never raise (`per_day` drops falsy results).

**Naming:** extractor `<signal>_day(day, payload)`; constants `MAX_DAYS_<SIGNAL>` with a trailing comment; tool `title` like "All-day stress".

**Expected payloads (verify, treat as hypotheses):**
- SpO2 `get_spo2_data(day)`: dict with `calendarDate`, `averageSpO2`, `lowestSpO2`, `latestSpO2`, `avgSleepSpO2`, `lastSevenDaysAvgSpO2`, `startTimestampGMT`/`startTimestampLocal`, and series `spO2HourlyAverages` / `continuousReadingDTOList` / `spO2ValueDescriptorsDTOList` + `spO2SingleValues` (shape varies; hourly averages are `[epoch ms GMT, value]` pairs).
- Respiration `get_respiration_data(day)`: dict with `calendarDate`, `lowestRespirationValue`, `highestRespirationValue`, `avgWakingRespirationValue`, `avgSleepRespirationValue`, `startTimestampGMT`/`startTimestampLocal`, and `respirationValuesArray` of `[epoch ms GMT, breaths/min]` about every 2 minutes (negative/null = no reading).

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation
Confirm library signatures/payload keys; add range constants.

### Phase 2: Core Implementation
**Depends on:** Phase 1
Two pure extractors in `garmin/extract.py`.

### Phase 3: Integration
**Depends on:** Phase 2
Two tool files, registration.

### Phase 4: Testing & Validation
**Depends on:** Phase 3
Extractor, tool and e2e tests; version bump; docs.

---

## STEP-BY-STEP TASKS

### CHECK garminconnect getters

- **IMPLEMENT**: `uv sync`, then read `get_spo2_data` and `get_respiration_data` in the installed library; compare the payload keys with the hypotheses above. If a key differs, use the library's real key and note it in the work item's Outcome. If `.env` credentials exist locally, optionally fetch one real day through the dev server (`local-dev-env` skill) and compare.
- **GOTCHA**: Payload keys are unverified (see Open Questions). Extractors must tolerate missing keys regardless.
- **VALIDATE**: `uv run python -c "import garminconnect as g; print(g.Garmin.get_spo2_data, g.Garmin.get_respiration_data)"`
- **SATISFIES**: AC #1, #2

### UPDATE src/my_garmin_mcp/garmin/dates.py

- **ADD**: `MAX_DAYS_SPO2 = 7  # one request per day, each day carries a time series` and `MAX_DAYS_RESPIRATION = 7  # same`
- **PATTERN**: `dates.py:11` (`MAX_DAYS_STRESS`)
- **GOTCHA**: Auto-decided 7 (see Assumptions); stays well under the 31-day per-day-tool cap.
- **VALIDATE**: `uv run ruff check src`
- **SATISFIES**: AC #5

### ADD spo2_day to src/my_garmin_mcp/garmin/extract.py

- **IMPLEMENT**: `spo2_day(day, payload, bucket_minutes=60)` returning `_clean({"date": payload.get("calendarDate") or day, "avg_spo2", "lowest_spo2", "latest_spo2", "avg_sleep_spo2", then if readings: "bucket_minutes", "columns": ["time","value"], "readings": [[HH:MM, mean]]})`. Valid SpO2 value: int/float (not bool) in 1..100 (Garmin uses 0/negative for no reading; drop). Shift GMT epoch ms to local with the offset from `startTimestampLocal - startTimestampGMT` via `_epoch_ms`, exactly as `stress_day` does. Use the first series that yields readings (hourly averages first, then the continuous-reading list); handle both `[ts, value]` rows and dict rows only if the real payload shows them. Fall back to the computed mean/min for avg/lowest when summary keys are missing. Return `None` when there are no readings and no summary value. Never raise on odd types.
- **PATTERN**: `extract.py:351-414` (`stress_day`), with `_stress_level` replaced by an SpO2 validator
- **GOTCHA**: Factor the shared local-time bucketing into a small private helper only if both new functions and `stress_day` can use it without changing `stress_day`'s behaviour; otherwise duplicate the few lines (do not refactor `stress_day` in this item). Reading units are percent. Keep 0 out of valid readings.
- **VALIDATE**: `uv run pytest tests/test_extract.py -q`
- **SATISFIES**: AC #1, #3

### ADD respiration_day to src/my_garmin_mcp/garmin/extract.py

- **IMPLEMENT**: `respiration_day(day, payload, bucket_minutes=30)` returning `date`, `lowest_respiration`, `highest_respiration`, `avg_waking_respiration`, `avg_sleep_respiration`, plus the bucketed `[time, value]` series from `respirationValuesArray` (same keys as above: `bucket_minutes`, `columns`, `readings`). Valid value: int/float (not bool) > 0 (and a sane upper bound, e.g. <= 100); negatives/null/0 are no reading. Round bucket means to 1 decimal (breaths/min is not an integer scale at this resolution; the SpO2 and stress means stay integers). Summary values from the payload when numeric and > 0, else computed min/max/mean of the readings (lowest/highest only). `None` when nothing usable.
- **PATTERN**: `stress_day` as above
- **VALIDATE**: `uv run pytest tests/test_extract.py -q`
- **SATISFIES**: AC #1, #3

### CREATE src/my_garmin_mcp/tools/spo2.py and respiration.py

- **IMPLEMENT**: copy `tools/stress.py`; names `get_spo2` (title "Blood oxygen (SpO2)") and `get_respiration` (title "Respiration"), fetch lambdas `g.get_spo2_data(d)` / `g.get_respiration_data(d)`, descriptions listing the fields and "At most N days per call; days without data are left out." Output keys `spo2` / `respiration`.
- **PATTERN**: `tools/stress.py:1-31`
- **IMPORTS**: `MAX_DAYS_SPO2` / `MAX_DAYS_RESPIRATION`, `spo2_day` / `respiration_day`, `EndDate, StartDate, as_json, per_day`
- **VALIDATE**: `uv run ruff check src && uv run ruff format --check src`
- **SATISFIES**: AC #1, #2, #5

### UPDATE src/my_garmin_mcp/tools/__init__.py

- **ADD**: import `respiration`, `spo2` (alphabetical in the import block) and add both to the `for module in (...)` tuple after `stress`.
- **VALIDATE**: `uv run python -c "import my_garmin_mcp.tools"`
- **SATISFIES**: AC #1

### UPDATE tests/test_extract.py

- **ADD**: for each extractor: summary + bucketing, local offset, ISO timestamps (if `_epoch_ms` path is used), invalid rows dropped and computed fallback, summary-only, parametrized empty/odd payloads (`None`, `{}`, `[]`, empty and all-invalid series, series is `5`) returning `None`, odd types never raise.
- **PATTERN**: `tests/test_extract.py:302-390`
- **VALIDATE**: `uv run pytest tests/test_extract.py -q`
- **SATISFIES**: AC #3, #4

### UPDATE tests/test_tools.py

- **ADD**: `get_spo2_data` and `get_respiration_data` methods on the fake API (record `self.calls`, return `{}`/empty for one day to show skipping), and per tool: returns days and skips empty ones, one request per day, rejects an 8-day range and a bad date.
- **PATTERN**: `tests/test_tools.py:40-50, 224-245`
- **VALIDATE**: `uv run pytest tests/test_tools.py -q`
- **SATISFIES**: AC #4, #5

### UPDATE tests/test_e2e.py

- **ADD**: `"get_spo2"`, `"get_respiration"` to the expected tool-name list (line ~60-75).
- **VALIDATE**: `uv run pytest tests/test_e2e.py -q`
- **SATISFIES**: AC #6

### UPDATE version (0.7.0 -> 0.8.0)

- **IMPLEMENT**: `version` in `pyproject.toml:3` and `__version__` in `src/my_garmin_mcp/__init__.py:2`, then `uv lock`.
- **VALIDATE**: `uv run pytest tests/test_version.py -q && uv lock --check`
- **SATISFIES**: AC #7

### UPDATE docs

- **IMPLEMENT**: `README.md`: replace the "Respiration, SpO2 | No" row (line 39) with two Yes rows (`get_spo2`, `get_respiration`), fix any tool counts; `AGENTS.md` ("twelve tools"/"eleven Garmin tools" and the tool list in Architecture become fourteen/thirteen and include the new names); also `docs/architecture/overview.md` and `.claude/skills/local-dev-env/SKILL.md` if they list tools (grep `get_stress`); `work/future-improvements.md:10`: remove SpO2 and respiration from the line (keep training status, hydration, floors, intensity minutes); bump `> Last updated:` on any edited doc and its area index entry per `docs/conventions/documentation.md`.
- **GOTCHA**: Keep real hostnames/paths out of docs.
- **VALIDATE**: `grep -rn "get_spo2\|get_respiration" README.md AGENTS.md docs work/future-improvements.md`
- **SATISFIES**: AC #8

---

## TESTING STRATEGY

pytest with the in-memory fake Garmin API; no network or credentials.

### Unit Tests
Extractors in `tests/test_extract.py` (fixtures built by small `_payload()` helpers like `_stress_payload`).

### Integration Tests
`tests/test_tools.py` (tools through an MCP client with the fake API) and `tests/test_e2e.py` (real server, tool list). Only these two files are run, each on its own, never `uv run pytest` over the whole suite during implementation tasks except the Level 2 command below.

### Edge Cases
Negative/zero/null readings; bool values; missing timestamps (offset 0); local offset shifting across midnight; summary without series; series without summary; whole payload `None`/`{}`; range over 7 days; invalid date.

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style
`uv run ruff check . && uv run ruff format --check .`

### Level 2: Unit Tests
`uv run pytest tests/test_extract.py tests/test_tools.py tests/test_version.py tests/test_garmin_client.py -q`

### Level 3: Integration Tests
`uv run pytest tests/test_e2e.py -q`

### Level 4: Manual Validation
If Garmin credentials are configured locally: `.claude/skills/local-dev-env/scripts/server.sh restart`, call `get_spo2` and `get_respiration` for one recent day and a 7-day range, check the payload size and that days without data are omitted. Otherwise record "not run (needs credentials)" in the Outcome, as earlier items did.

### Level 5: Additional Validation
`uv lock --check`

---

## ACCEPTANCE CRITERIA

- [ ] `get_spo2` and `get_respiration` exist, take `start_date`/`end_date`, and return compact JSON with per-day summary and downsampled `[time, value]` readings
- [ ] Both use `per_day` (one request per day, 3 at a time) and a range limit of 7 days; longer ranges give an `InvalidRequest`
- [ ] Extractors are pure, never raise on odd payloads, and return `None` for empty days
- [ ] Unit, tool and e2e tests cover both tools; ruff clean
- [ ] Failures surface as `ToolError`s
- [ ] Version bumped consistently (0.8.0) and `uv.lock` updated
- [ ] README/AGENTS.md/architecture docs updated; SpO2/respiration removed from `work/future-improvements.md`
- [ ] No regressions in existing tests

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed
- [ ] Level 1-3 commands pass
- [ ] Acceptance criteria met
- [ ] Outcome in the work item notes any payload-key deviation from this plan

---

## OPEN QUESTIONS / ASSUMPTIONS

No gate questions: the work item leaves the one-vs-two-tools call to this plan, and everything else is contained to this item and cheap to change.

- Auto-decided — one combined tool or two: two tools (`get_spo2`, `get_respiration`) — separate endpoints and payloads, avoids doubling requests; reversible by adding a wrapper later.
- Auto-decided — range limit: 7 days for both, same as `get_stress` — each day carries a series; easy to raise later.
- Auto-decided — series granularity: SpO2 60-minute buckets (Garmin's own series is hourly-ish and sparse), respiration 30-minute buckets, same pattern as stress/heart rate; function default parameters, not exposed to callers.
- Auto-decided — output field names (`avg_spo2`, `lowest_spo2`, `avg_sleep_spo2`, `latest_spo2`, `lowest_respiration`, `highest_respiration`, `avg_waking_respiration`, `avg_sleep_respiration`): consistent with the `avg_spo2`/`lowest_spo2`/`avg_respiration` names in `sleep_summary` — only this server's own output, cheap to rename before release.
- Assumed — the payload keys listed under Patterns are correct, confirm in the CHECK task (the library was not installed in the planning checkout and no Garmin credentials were available); where they differ, follow the real payload.

## NOTES (open canvas)

- Rejected: one combined tool returning both per day — two requests per day for callers who want one signal, and a larger payload on the phone.
- Rejected: refactoring `stress_day` to share bucketing — widens the diff and risks regressions on a shipped tool; a shared helper can be a follow-up.
- `get_sleep` already includes the night's avg/lowest SpO2 and avg respiration; the new tools add the all-day picture and series. Descriptions should say so to help Claude pick the right tool.

## AMENDMENTS

