# Legacy project: my-garmin-api

Source (read-only, to be deleted): `/home/jackisback/WslCode/garmin/my-garmin-api`
All paths below are relative to that directory. Documented from the files themselves; items marked **(uncertain)** were not fully verified. Secrets are redacted.

## 1. Overview and tech stack

- Python FastAPI service ("My Garmin API") that wraps Garmin Connect via the community `garminconnect` library and exposes JSON over REST, mainly for ChatGPT-Action/OpenAPI use and later an MCP bridge. README warns "not production ready".
- Author: Adam Jakab. Version `1.0.0` in `pyproject.toml` (the unused-by-default health route reads it; README sample says 0.1.3, FastAPI app says 0.1.0: inconsistent).
- Git: 1 branch (`main`), ~20+ commits, 2026-04-08 (init) to 2026-09-29. No tags. Last commit: "Delete invalid Garmin token store before fresh login".
- No tests, no Dockerfile, no CI, no deploy files, no scripts besides the two `uv` entry points.

Stack (from `pyproject.toml`):

| Item | Value |
| --- | --- |
| Language/runtime | Python >=3.10,<4.0 (the local `.venv` is Python 3.11) |
| Package manager/build | `uv`, build backend `uv_build>=0.11.7,<0.12.0` |
| garminconnect | `>=0.3.2,<0.4.0`. `uv.lock` has two resolutions: 0.3.2 (Python <3.12, what `.venv` has) and 0.3.17 (Python >=3.12) |
| curl-cffi | `>=0.16.0,<0.17.0` (TLS fingerprint impersonation used by garminconnect login) |
| fastapi | `>=0.100.0,<1.0.0`; uvicorn `>=0.24.0,<1.0.0` |
| pydantic | v2 (2.13.5 in `.venv`, transitive via fastapi) |
| python-dotenv | `>=1.1.0,<2.0.0` |
| requests | `>=2.33.1,<3.0.0`; ua-generator `>=2.0.24,<3.0.0`; tomli `>=2.4.1,<3.0.0` (only for the health route) |
| Lint config | pylint (max line 120) and ruff (line-length 120) in `pyproject.toml` |

## 2. Directory map

```text
pyproject.toml                         manifest, deps, console scripts, lint config
uv.lock                                lockfile
README.md                              user docs (partly stale, see section 8)
.env.example                           env template (placeholders)
.env                                   REAL local env (gitignored, contains secrets; not reproduced here)
.gitignore                             ignores .venv, .env*, tmp/, cache/, __pycache__
.github/copilot-instructions.md        notes: no nullable date params for ChatGPT OpenAPI; date-range endpoints require both dates
.vscode/settings.json                  editor settings only
tmp/garmin_tokens.json                 LIVE persisted Garmin token file (gitignored; keys: di_token, di_refresh_token, di_client_id; values NOT copied)
cache/                                 empty dir
my_garmin_api/__init__.py              calls dotenv.load_dotenv() on import
my_garmin_api/garmin_fit.py            CORE: auth_garmin() + all Garmin data functions (507 lines)
my_garmin_api/helpers/activity_enrichment.py  map of activity sub-resource name -> garminconnect call
my_garmin_api/helpers/activity_details.py     aggregate_activity_details(): columnar metrics -> 60s buckets (min/max/avg/count)
my_garmin_api/helpers/file_cache.py    generic JSON file cache (md5 key, TTL) - UNUSED anywhere
my_garmin_api/api.py                   FastAPI app, middleware, uvicorn launchers (REST-only)
my_garmin_api/api_auth.py              X-API-Key check (REST-only)
my_garmin_api/api_routes/__init__.py   discover_routers(): auto-imports modules not starting with "_"
my_garmin_api/api_routes/_healthcheck.py  GET / (disabled by leading underscore; docstring says DISABLED)
my_garmin_api/api_routes/activities_by_date.py GET /activities
my_garmin_api/api_routes/activity.py   GET /activity/{activity_id}
my_garmin_api/api_routes/{hrv,rhr,sleep,vo2max,weight}.py  one GET route each
my_garmin_api/api_routes/schemas/*.py  40 pydantic response models (REST-only; useful as field documentation)
```

Stale `__pycache__` files hint at removed modules: `main`, `activity_cache`, `garmin_cache`, `workouts`, `_workouts`, `workouts_by_date` (workouts endpoints existed once and were removed; source not in tree or git HEAD **(uncertain: git history not inspected for their content)**).

## 3. Authentication with Garmin Connect

All in `my_garmin_api/garmin_fit.py`: `auth_garmin()`, `_token_store_file()`, `_clear_token_store()`.

- Library: `garminconnect` (`Garmin` class, `garminconnect/client.py` does the login). No Garth/OAuth1: version 0.3.x uses Garmin "DI" OAuth2 tokens.
- Login strategy chain inside the library (tried in order; only credential errors stop the chain): mobile iOS + curl_cffi, mobile iOS + requests, SSO widget + cffi, portal web + cffi (10-20 s anti-WAF delay), portal web + requests. Endpoints: `diauth.garmin.com/di-oauth2-service/oauth/token` for token exchange; SSO service URLs under `mobile.integration.garmin.com/gcm/ios|android` and `connect.garmin.com/app`.
- Token store: path from env `GARMIN_TOKEN_STORE`, default `~/.garminconnect`, `expanduser`-ed. Library writes `garmin_tokens.json` inside it (if path is a dir or does not end in `.json`; else the path itself is the file). File content is a JSON object with exactly `di_token`, `di_refresh_token`, `di_client_id`, written as plain text with no chmod. The live project actually has one at `tmp/garmin_tokens.json` (from `.env` `GARMIN_TOKEN_STORE`, value redacted).
- Flow of `auth_garmin()` (called on EVERY data request, builds a new `Garmin` each time; no singleton/caching of the client):
  1. `Garmin().login(tokenstore_path)` with no credentials: restores tokens; prints "Authenticated using saved tokens."; returns client.
  2. `GarminConnectTooManyRequestsError` (429): print and `sys.exit(1)` (kills the whole process; poor for a long-lived server).
  3. `GarminConnectAuthenticationError` / `GarminConnectConnectionError` on restore: deletes the token file (`_clear_token_store`, last commit's fix) and falls through.
  4. Fresh login loop: requires `GARMIN_EMAIL`/`GARMIN_PASSWORD` (RuntimeError if missing), `Garmin(email, password, prompt_mfa=lambda: input("MFA code: ").strip())`, `login(tokenstore_path)`; the library dumps tokens to the store after login. Errors: 429 -> exit(1); auth error ("Wrong credentials.") -> returns None; connection error -> returns None; Ctrl-C -> None.
- MFA: only via interactive stdin `input()` prompt. Not usable headless/under an MCP stdio server. The library also supports `return_on_mfa=True` plus `resume_login(client_state, mfa_code)` (`garminconnect/__init__.py` ~lines 469-622 in 0.3.2) which is NOT used here; recommended for the new project (or provide a separate one-time CLI login script that writes the token file).
- Token refresh: library does `_refresh_di_token` / `_refresh_session` internally; this project does nothing explicit.
- All data functions return `None` when `auth_garmin()` returns None; routes turn that into empty/404 responses (REST semantics, errors are swallowed).

## 4. Garmin Connect capabilities wrapped

All are plain functions in `my_garmin_api/garmin_fit.py` (core logic) wrapped by routes. Garmin paths are from the installed `garminconnect` 0.3.2 (`.venv/.../garminconnect/__init__.py`), relative to the Connect API base (proxy) that the library handles. Inputs are `datetime.date`; ranges are inclusive. Date ranges are fetched by looping day by day (one HTTP call per day, sequential) except weight and activities.

| Capability | Function / REST route | Params | Garmin call (library method -> endpoint) | Return shape |
| --- | --- | --- | --- | --- |
| Activities list | `get_activities_for_date_range` / `GET /activities` (`api_routes/activities_by_date.py`) | `start_date`, `end_date` (both required, 400 if end<start) | `get_activities_by_date(startdate, enddate)` -> `/activitylist-service/activities/search/activities` (paged 20 at a time by the library) | `{start_date,end_date,count,activities:[{activity_id,summary:<raw Garmin activity>,errors?}]}`. Summary only, NO enrichment on the list (README claims enrichment: stale) |
| Single activity | `get_activity_by_id` / `GET /activity/{activity_id}` (`api_routes/activity.py`) | path `activity_id`; Y/N flags (default N): `details, splits, typed_splits, split_summaries, exercise_sets, hr_time_in_zones, power_time_in_zones, weather, gear` | `get_activity` -> `/activity-service/activity/{id}`; then per flag (see `helpers/activity_enrichment.py`): `/details`, `/splits`, `/typedsplits`, `/split_summaries`, `/exerciseSets`, `/hrTimeInZones`, `/powerTimeInZones`, `/weather`, and gear via `/gear-service/gear/filterGear` | `{activity_id, summary, <each enabled key>}`. Summary is flattened: `summaryDTO` merged to top level, `activityTypeDTO` renamed `activityType`. `None` -> 404. |
| Activity detail metrics | `aggregate_activity_details` (`helpers/activity_details.py`) | `details` raw payload, bucket 60 s | `get_activity_details` -> `/activity-service/activity/{id}/details` | `{aggregationInterval, metrics:{<key>:[{timestamp(ms),min,max,avg,count}]}}`; uses `metricDescriptors` (key/metricsIndex) and `directTimestamp`; reduces large time series |
| HRV | `get_hrv_for_date_range` / `GET /hrv` | `start_date`,`end_date` | `get_hrv_data(date)` -> `/hrv-service/hrv/{date}` | `{..., count, hrv_data:[{date, hrv:<Garmin payload minus hrvReadings>}]}`; days with None skipped; schema `schemas/hrv.py` documents hrvSummary/baseline fields (weeklyAvg, lastNightAvg, lastNight5MinHigh, baseline lowUpper/balancedLow/balancedUpper/markerValue, status etc.) |
| Resting HR | `get_rhr_for_date_range` / `GET /rhr` | same | `get_rhr_day(date)` -> `/userstats-service/wellness/daily/{displayName}` with `fromDate=untilDate=date`, `metricId=60` | `rhr_data:[{date, rhr:<raw dict>}]` |
| Weight/body composition | `get_weight_for_date_range` / `GET /weight` | same | `get_body_composition(start,end)` -> `/weight-service/weight/dateRange` (single call) | `weight_data:[{date(calendarDate or start fallback), weight:<raw dateWeightList item>}]` |
| Sleep | `get_sleep_for_date_range` / `GET /sleep` | same | `get_sleep_data(date)` -> `/wellness-service/wellness/dailySleepData/{displayName}` with `date`, `nonSleepBufferMinutes=60` | `sleep_data:[{date, sleep:{score,duration_seconds}}]` ONLY. Score from `dailySleepDTO.sleepScores.overall.value`, fallbacks `dailySleepDTO.sleepScore.overallScore` and top-level `sleepScore.overallScore`; duration from `dailySleepDTO.sleepTimeSeconds` (fallback top-level). Days with both None skipped. No stages, SpO2, respiration, etc. |
| VO2 max | `get_vo2max_for_date_range` / `GET /vo2max` | same | `get_max_metrics(date)` -> `/metrics-service/metrics/maxmet/daily/{date}/{date}` | `vo2max_data:[{date, vo2max_precise_value: max float per date}]`. Recursively searches payload for keys containing "vo2" and `vo2MaxPreciseValue`; dates outside the range dropped; helper fns `_contains_vo2max_data`, `_extract_vo2max_metrics`, `_extract_metric_calendar_date`, `_extract_vo2max_precise_values` |
| Health check | `api_routes/_healthcheck.py` `GET /` | none | none | `{status,message,version}`; DISABLED (file name starts with `_`) though README still documents it |

Response schemas (REST-only pydantic, but good reference for field names): `schemas/activity_summary.py` (359 lines), `activity_splits.py`, `activity_details.py`, `activity_gear.py`, `activity_weather.py`, `activity_exercise_sets.py`, `activity_typed_splits.py`, `activity_split_summaries.py`, `activity_hr_time_in_zones.py`, `activity_power_time_in_zones.py`, plus per-metric files. Many fields are Optional/ignore-extra.

NOT wrapped (never implemented here, though `garminconnect` offers them, ~94 getters): stress (`get_stress_data` -> `/wellness-service/wellness/dailyStress/{date}`), body battery, steps, intraday/daily heart rate, training readiness, training status, SpO2, respiration, hydration, floors, intensity minutes, devices, user summary, workouts (list/upload/schedule; library has `workout.py`, `fit.py`), goals, badges, gear management, hill score, lactate threshold, FTP etc. Sleep stages are not returned by this project.

## 5. REST layer: drop vs reusable

REST-only, safe to drop: `my_garmin_api/api.py`, `api_auth.py`, `api_routes/**` (all route files, `__init__.py` router discovery, `_healthcheck.py`), `api_routes/schemas/**` (convert useful ones to zod/TS types if wanted), FastAPI/uvicorn/tomli deps, `API_KEY`/`API_HOST`/`API_PORT`/`API_RELOAD`/`OPENAPI_SERVERS`, HTTP error mapping (400/404/500), the Y/N flag query params (replace with MCP tool input schemas).

Reusable core logic (port to TypeScript): everything in `garmin_fit.py` and `helpers/`. Route files contain the tool descriptions (summary/description text) worth reusing as MCP tool descriptions, plus the validation rule `end_date >= start_date` and the "404 when empty" semantics.

## 6. Config, scripts, commands

Env vars (loaded by `python-dotenv` in `my_garmin_api/__init__.py`):

| Var | Used by | Default / note |
| --- | --- | --- |
| `GARMIN_EMAIL`, `GARMIN_PASSWORD` | `auth_garmin` | required for fresh login (values redacted) |
| `GARMIN_TOKEN_STORE` | `auth_garmin` | `~/.garminconnect`; `.env.example` uses it that way |
| `GARMIN_CACHE_FOLDER` | `helpers/file_cache.py` (unused) | `./tmp` in `.env.example`. README says activities are cached: not true in current code |
| `GARMIN_CACHE_EXPIRATION_SECONDS` | `helpers/file_cache.py` (unused) | 3600 in `.env.example`; code default 86400 |
| `API_KEY` | `api_auth.py` | required, `X-API-Key` header, `secrets.compare_digest` |
| `API_HOST`, `API_PORT`, `API_RELOAD` | `api.py` | dev 127.0.0.1:8000 reload; prod 0.0.0.0:8000 |
| `OPENAPI_SERVERS` | `api.py` | comma-separated URLs |

Commands: `uv sync`; `uv run api` (prod defaults); `uv run api-dev` (reload); console scripts `api = my_garmin_api.api:main`, `api-dev = my_garmin_api.api:main_dev`. Docs at `/docs`, `/openapi.json`, `/redoc`. Tests: none. Lint: pylint/ruff configured, no commands recorded. Docker/deploy: none (README suggests ngrok/tunnel for ChatGPT).

## 7. What to port / what to drop

| Port | From | Notes |
| --- | --- | --- |
| Auth flow (restore tokens -> clear bad store -> credential login -> persist) | `garmin_fit.py` `auth_garmin`, `_token_store_file`, `_clear_token_store` | Rewrite with a Node library (see risks). Replace `sys.exit` with thrown errors; cache one client instance; non-interactive MFA |
| Token file format and path logic | same | `garmin_tokens.json` with `di_token`, `di_refresh_token`, `di_client_id`; directory-or-`.json` rule |
| Date-range looping helpers | each `get_*_for_date_range` | Consider parallelism with a concurrency limit; keep inclusive ranges |
| Sleep score/duration extraction with legacy fallbacks | `get_sleep_for_date_range` | Good candidate for a richer `get_sleep` tool |
| VO2 max recursive extraction | `get_vo2max_for_date_range` + 4 helpers | Handles inconsistent payload shapes |
| HRV sanitizing (drop `hrvReadings`) | `get_hrv_for_date_range` | Keeps responses small for LLM context |
| Activity detail time-bucket aggregation | `helpers/activity_details.py` | Valuable for token-size control |
| Activity enrichment registry and summary flattening | `helpers/activity_enrichment.py`, `get_activity_by_id` | Map to optional MCP tool args/`include` array |
| Weight/body-composition list extraction | `get_weight_for_date_range` | |
| Tool descriptions | `api_routes/*.py` | Reword for MCP |
| Field reference | `api_routes/schemas/*.py` | Reference for zod output schemas |

| Drop | Reason |
| --- | --- |
| `api.py`, `api_auth.py`, `api_routes/`, FastAPI/uvicorn, API_KEY, OpenAPI settings | REST layer |
| `helpers/file_cache.py` | unused; re-evaluate caching only if needed (could be reimplemented) |
| `.venv`, `__pycache__`, `uv.lock`, `.vscode`, `tmp/`, `cache/` | build/local artifacts; `tmp/garmin_tokens.json` is a live credential, do not copy into the repo |
| `.github/copilot-instructions.md` | REST/ChatGPT specific (idea worth keeping: required date params, same date for single day) |

## 8. Available vs. missing / incomplete

Available: activities by date range (summary), single activity with 9 optional enrichments, HRV, resting HR, weight/body composition, sleep (score+duration only), VO2 max, token persistence with automatic invalid-token cleanup.

Gaps / issues:

- No stress, body battery, steps, heart-rate series, training readiness/status, SpO2, respiration, sleep stages, workouts (previously existed per stale pycache, then removed), devices, etc.
- No tests anywhere; no CI; no Docker/deploy.
- README stale: says `start_date` optional for `/activities` (code requires both), says activities are enriched and cached (list returns summary only; cache is unused), documents `GET /` health (disabled), version strings disagree (0.1.0 / 0.1.3 / 1.0.0), mentions `uv run api-dev` reload dirs.
- `get_activity_by_id`: only catches `GarminConnectConnectionError`; enrichment errors are not collected into `errors` (the schema has `errors` field, only the list endpoint's missing-id case fills it). If one enrichment call fails the whole request 500s.
- MFA prompts via stdin `input()`; headless use will hang/fail.
- 429 -> `sys.exit(1)` inside library-calling function kills the server.
- `auth_garmin()` builds and logs in a new client for every call (every call hits token restore, and a failure path can trigger credential logins repeatedly: rate-limit risk). Auth failures return `None` and get reported as empty/404, hiding the real cause.
- Auth failure logging prints all request headers (including `X-API-Key`) to logs (`api.py`, `api_auth.py`): leaks the key; REST-only, don't port.
- Day-by-day sequential requests for HRV, RHR, sleep, VO2max: slow for long ranges, no max-range limit.
- Weight with missing `calendarDate` falls back to `from_date` (may mislabel).
- Tokens stored as plain JSON without restricted permissions.
- `pyproject.toml` pylint `ignore-paths` mentions `my_garmin_api/garminconnect` (a vendored copy that no longer exists).

## 9. Open questions and risks

- Node library choice: `garminconnect` is Python-only. Need a Node/TS equivalent (candidates exist on npm, e.g. `garmin-connect`; not evaluated here **(uncertain)**), or reimplement the DI OAuth2 flow (mobile iOS SSO + `diauth.garmin.com` token exchange; see `garminconnect/client.py` in `.venv` as a reference implementation), or call this logic via a Python subprocess. Verify that the npm library supports current Garmin auth (Garmin changed login in 2025/2026; the library above has a 5-strategy chain for exactly this reason, including TLS fingerprint impersonation via curl_cffi that plain Node `fetch` lacks, so Cloudflare blocking is a real risk).
- Headless MFA and token bootstrap for a remote/mobile-served MCP server: decide on a one-time CLI login that writes the token file, token refresh behavior, and where tokens live (volume/secret store).
- Garmin API is unofficial; endpoints and payload shapes may change without notice; display name is required for some endpoints (`_require_display_name` in library for RHR, `display_name` for sleep), so profile loading after login matters.
- Rate limits (429) and Cloudflare blocks (README troubleshooting: stop retrying, wait).
- Response size for LLM context: keep sanitization/aggregation (HRV readings dropped, 60 s buckets).
- Which capabilities does the Claude mobile app need beyond what existed (stress, body battery, steps, HR)? Not specified in the source project.
- Whether to keep any caching (existing helper unused).
- Not verified: contents of removed workouts modules; exact installed 0.3.17 behavior (only 0.3.2 is installed locally).
