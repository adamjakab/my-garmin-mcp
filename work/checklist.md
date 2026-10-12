# Checklist: reach parity with the legacy setup

Goal: Claude (including the mobile app) can read the same Garmin data it could through the two legacy projects (`my-garmin-api` + `adam_mcp`), served by this project alone. Details of what existed are in [docs/legacy/](../docs/legacy/).

Done so far: Python (uv) server scaffold, `ping` tool, access key, `.env`, dev loop (see [AGENTS.md](../AGENTS.md)).

## 1. Garmin login

- [x] Use `garminconnect` (cyberjunky; decided over the Node `garmin-connect`). Spike done 2026-10-12: login with the `.env` credentials works (0.3.17, ~10 s, a few login strategies get a 429 before one succeeds), tokens are saved to `<GARMIN_TOKEN_STORE>/garmin_tokens.json` (the path is a directory) and the next login reuses them in ~0.5 s. `get_sleep_data` and `get_rhr_day` returned data. Tokens are only saved when `return_on_mfa` is off.
- [x] One shared client, created once and reused (the legacy API logged in on every request): `GarminClient` in `src/my_garmin_mcp/garmin/client.py`, logins serialised, calls run in worker threads
- [x] Persist session tokens in `GARMIN_TOKEN_STORE` and refresh them; fall back to a credential login only when needed (verified: works from the token file with no credentials; a failed login is not retried for 15 minutes)
- [x] Errors are thrown and returned as tool errors, never crash the process (the legacy code exited on HTTP 429): the client raises `GarminError` with a safe message; tools must let it surface as a tool error
- [ ] Decide how to handle MFA, if the account ever asks for it (e.g. a one-time CLI login that writes the token file)

## 2. Tools (the legacy set)

All date-range tools take `start_date` and `end_date` (YYYY-MM-DD, inclusive, end >= start).

- [ ] `get_sleep`: score and duration per day (consider adding sleep stages)
- [ ] `get_hrv`: per day, dropping the bulky raw readings
- [ ] `get_resting_hr`
- [ ] `get_vo2max`
- [ ] `get_weight`: body composition
- [ ] `get_activities`: list for a date range
- [ ] `get_activity`: one activity by id, with optional extras (details, splits, typed splits, split summaries, exercise sets, HR zones, power zones, weather, gear)
- [ ] Activity details reduced to 60-second buckets (min/max/avg/count) to keep responses small

## 3. Shared quality

- [ ] Tool descriptions written for Claude, reusing the legacy wording where good
- [ ] Output sizes kept manageable for the phone's context
- [ ] Tests: pure logic (date ranges, sleep/VO2 extraction, bucketing) and each tool through the e2e client
- [ ] Each tool tried for real through `Garmin-MCP-Local` against the actual account

## 4. Reachable from the phone (deploy to vps2)

- [ ] Get the code and a production `.env` onto vps2 (own access key, Garmin credentials); install with `uv sync --no-dev`; PM2 starts `uv run python -m my_garmin_mcp`
- [ ] Run under PM2 as `my-garmin-mcp` (add an ecosystem file) and make it survive reboots (`pm2 startup` + `pm2 save`)
- [ ] Pick a hostname and add a DNS record pointing it at vps2 (the name itself is kept out of the repo; it lives in the NGINX config on the server)
- [ ] NGINX: a server block for that hostname that proxies HTTPS to the app on `127.0.0.1:3334`
  - [ ] TLS certificate (e.g. Let's Encrypt via certbot) and an HTTP-to-HTTPS redirect
  - [ ] Location exactly `/mcp` (no trailing slash), proxy buffering off, sensible timeouts
  - [ ] Its own rate limit, and no logging of the `Authorization` header
- [ ] Add it as a custom connector in Claude with the `Authorization: Bearer <key>` request header
- [ ] Ask for each tool's data from the phone and compare with the legacy answers
- [ ] Write the deploy and update steps down (a short doc under `docs/`) so redeploys are repeatable

## 5. Wrap-up

- [ ] Anything still worth keeping from the legacy projects is ported here
- [ ] Delete the two legacy projects
- [ ] Remove `docs/legacy/` and update the migration section in `AGENTS.md`
- [ ] Before going public: review history and files for secrets and local paths

## Later (not needed for parity)

Data the legacy setup never offered: stress, body battery, steps, heart rate, training readiness and status, SpO2, workouts, devices.
