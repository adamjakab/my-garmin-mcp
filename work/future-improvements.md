# Future improvements

Notes, not committed work. Turn an item into a work item (`work/open/`) when it is picked up.

## More Garmin data

Not exposed yet; `garminconnect` has getters for all of them.

- Training status, hydration
- Devices, user summary, workouts (list and schedule), goals, badges
- Lactate threshold, FTP, hill score and other performance metrics
- `get_activities`: filter by activity type, and paging if a range gets long

## Robustness

- **MFA:** nothing handles it yet. The library only saves tokens when `return_on_mfa` is off (it returns early otherwise), so a one-time CLI login that writes the token file is the likely route if the account ever asks for a code.
- **Paths never exercised for real:** the token deletion after 3 rejections (tested with fakes only), the token refresh close to expiry, and `deploy/update.sh` with a red test run or a failed health check (rollback). Only the green path ran on vps2.
- **Body composition:** only `weight_kg` has been seen, because the scale or app logs weight only. The other fields (`body_fat_pct`, `muscle_mass_kg`, ...) assume Garmin reports grams and are untested with real data.
- **Tool output** arrives wrapped as `{"result": "<escaped JSON>"}` because tools return compact JSON text. Returning structured content would avoid the escaping but pretty-prints long number lists; measure before changing.
- Per-day tools make one Garmin request per day (3 at a time, max 31 days). If Garmin rate limits become a problem, add a small cache.

## Operations

- `deploy/update.sh` only runs the tests; a `ruff check` gate would be one more line.
- Rotating the access key means editing the Claude connector header by hand; there is no overlap period where two keys work.
