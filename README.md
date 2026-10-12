# my-garmin-mcp

A personal MCP server (Python) that lets Claude, including the mobile app, read the owner's Garmin data through a handful of tools. See [docs/](docs/) for how it works and how to run it.

## Documentation

- [Architecture](docs/architecture/README.md) — how the server is built and why: transport, auth, the shared Garmin session, tool design.
- [Setup](docs/setup/README.md) — from clone to a running local server, configuration and tests.
- [Deployment](docs/deployment/README.md) — how it ships and runs in production (PM2, NGINX, updates).
- [Conventions](docs/conventions/README.md) — rules for working in this repo: versioning, workspace boundaries, documentation.

## Garmin coverage

What the `garminconnect` library can reach, and which parts this server exposes. The server is read-only, so none of the write actions are available.

| Function | Available via the MCP? |
| --- | --- |
| Sleep data | Yes (`get_sleep`) |
| Heart rate variability (HRV) | Yes (`get_hrv`) |
| Resting heart rate | Yes (`get_resting_hr`) |
| VO2 max | Yes (`get_vo2max`) |
| Weight | Yes (`get_weight`) |
| Activity lists | Yes (`get_activities`) |
| **Activity (`get_activity`)** | **Yes, summary by default, plus these extras:** |
| &nbsp;&nbsp;↳ Details | Yes (extra `details`) |
| &nbsp;&nbsp;↳ Splits | Yes (extra `splits`) |
| &nbsp;&nbsp;↳ Typed splits | Yes (extra `typed_splits`) |
| &nbsp;&nbsp;↳ Split summaries | Yes (extra `split_summaries`) |
| &nbsp;&nbsp;↳ Exercise sets | Yes (extra `exercise_sets`) |
| &nbsp;&nbsp;↳ HR zones | Yes (extra `hr_zones`) |
| &nbsp;&nbsp;↳ Power zones | Yes (extra `power_zones`) |
| &nbsp;&nbsp;↳ Weather | Yes (extra `weather`) |
| &nbsp;&nbsp;↳ Gear used | Yes (extra `gear`) |
| Daily summary, steps, floors | No |
| All-day heart rate | No |
| Stress, body battery | No |
| Respiration, SpO2 | No |
| Intensity minutes | No |
| Hydration | No |
| Training readiness, training status | No |
| Endurance score, hill score | No |
| Max metrics, fitness age | No |
| Race predictions, lactate threshold | No |
| Body composition details, weigh-in add or delete | No |
| Blood pressure | No |
| Activity download (FIT, TCX, GPX, KML, CSV) | No |
| Activity upload, manual activity create, rename, delete | No |
| Workouts and training plans | No |
| Personal records, badges, challenges, goals | No |
| Devices, alarms, device settings | No |
| Gear list, gear stats, gear defaults | No |
| User profile and settings, social profile, connections | No |
| Menstrual and pregnancy data | No |
| Golf data | No |
| Connect+ (premium) features | No |
| `ping` (health and version check) | Yes, but it isn't a Garmin function |

> Whatever is a "No" above, read it: "Not yet".

## License

MIT, see [LICENSE](LICENSE).
