# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Live. A Python MCP server (Python >= 3.12, managed with `uv`, official `mcp` SDK v2 `MCPServer`, Starlette/uvicorn) with API-key auth and eight tools: `ping` and seven Garmin tools (sleep, HRV, resting heart rate, VO2 max, weight, activities, one activity with extras), backed by the `garminconnect` library (cyberjunky). It runs on vps2 under PM2 behind NGINX and is used as a custom connector from Claude Code and the Claude mobile app. Ideas for later are in [work/future-improvements.md](work/future-improvements.md);; the checklist that took it live is [work/checklist.md](work/checklist.md).

## Commands

- `uv sync` - install dependencies into `.venv`
- `uv run python -m my_garmin_mcp` - foreground server
- `scripts/server.sh start|stop|restart|status|logs` - background server (pid/log in `.run/`); restart after code changes so the tool list refreshes
- `uv run rotate-key` - asks for confirmation (warns that clients using the old key break), then writes a new `MCP_ACCESS_KEY` into `.env` and prints it. Restart afterwards (`pm2 restart my-garmin-mcp` in production). `--yes` skips the prompt
- `uv run pytest` (includes an end-to-end MCP client test), `uv run ruff check .`, `uv run ruff format .`

Config via `.env` (copy `.env.example`; gitignored): `PORT`, `HOST`, `ALLOWED_HOSTS` (public hostname(s) behind a reverse proxy; loopback is always allowed), `DATA_DIR`, `GARMIN_EMAIL`, `GARMIN_PASSWORD`, `GARMIN_TOKEN_STORE`, `MCP_ACCESS_KEY` (the single access key). Real env vars override the file.

Deploy and update steps: [docs/deploy.md](docs/deploy.md) (with the NGINX and PM2 config as appendices); `deploy/update.sh` on vps2 tests `origin/main` in a throwaway worktree and, only if green, restarts the pm2 app. Production runs under PM2 as `my-garmin-mcp` (assumed name, same as the project). After changing `.env` or deploying, restart it with `pm2 restart my-garmin-mcp`. `scripts/server.sh` is for local development only.

## Architecture

- Streamable HTTP at `/mcp` via `MCPServer.streamable_http_app`, **stateless** and JSON responses (no sessions to lose on restart), guarded by `Authorization: Bearer <key>`. `GET /health` is unauthenticated.
- `src/my_garmin_mcp/tools/` - one file per tool, each exposing `register(server)`, wired up in `tools/__init__.py`.
- Tools (`get_sleep`, `get_hrv`, `get_resting_hr`, `get_vo2max`, `get_weight`, `get_activities`, `get_activity`) are thin: the payload-shaping logic is in `garmin/extract.py` (pure, unit-tested) and date handling in `garmin/dates.py` (range limits, bounded parallelism). They return compact JSON text to keep phone context small. Failures must be `ToolError`s (`GarminError`, `InvalidRequest`): any other exception reaches Claude only as "Error executing tool".
- `src/my_garmin_mcp/auth/` - the single access key from `MCP_ACCESS_KEY` (compared as SHA-256 digests in constant time), the pure-ASGI bearer middleware, and the `rotate-key` script.
- `app.py` builds the ASGI app, `server.py` the `MCPServer`, `config.py` reads `.env`.
- `src/my_garmin_mcp/garmin/client.py` - `GarminClient`, the one shared Garmin session (tools call `await garmin.call(lambda g: g.get_...(...))`). It restores/refreshes the saved tokens and only uses the credentials when that fails, so a login never happens per request. After a failed login it pauses 15 minutes instead of retrying, to avoid Garmin blocking the IP. If the saved tokens are rejected 3 times in a row (`MAX_AUTH_FAILURES`) the token file is deleted so the next login is fresh (kept if no credentials are configured); this and login failures are logged at WARNING/ERROR to stderr (`.run/server.log` locally, the PM2 log in production). Raises `GarminError`.
- No database; runtime state (e.g. Garmin tokens) lives in `data/` (gitignored).

## Connecting Claude Code to the local server

`claude mcp add --transport http my-garmin http://127.0.0.1:3334/mcp --header "Authorization: Bearer <key>"`

## Conventions

- Version bumps: change `version` in `pyproject.toml` **and** `__version__` in `src/my_garmin_mcp/__init__.py` (a test fails if they differ), then run `uv lock` so `uv.lock` follows (the deploy installs with `--locked`). `ping` reports the version, which is how to confirm what is deployed.
- [Workspace boundaries](docs/conventions/workspace-boundaries.md) - read sibling projects freely, write only inside `my-garmin-mcp/`.

## Purpose

A personal MCP (Model Context Protocol) server, written in Python, that lets the Claude mobile app talk to the owner's Garmin account. It fetches health data from Garmin and serves it back to Claude through MCP tools.
