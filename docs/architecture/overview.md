# Architecture overview

> Last updated: 2026-10-12

The mental model of the server and the reasons behind its main design choices. The code carries the details; this explains the shape.

## Shape

Claude (Code or the mobile app) calls the server over MCP streamable HTTP at `/mcp`. A bearer-key middleware guards it, tools call one shared Garmin session, and the pure shaping logic turns Garmin's large responses into small payloads.

```
Claude -> NGINX (prod) -> BearerAuthMiddleware -> MCPServer /mcp -> tools -> GarminClient -> Garmin Connect
```

## Decisions and why

- **Stateless HTTP with JSON responses.** No sessions exist, so a restart or deploy loses nothing and clients never need to reconnect.
- **One access key, compared as SHA-256 digests in constant time.** A personal server needs one key, not a user system. Rotation is a script, at the cost of no overlap period between old and new key.
- **Allowed hosts list.** The SDK rejects unknown Host headers (DNS rebinding protection). Loopback is always allowed; the public hostname goes in `ALLOWED_HOSTS`.
- **One shared `GarminClient`.** Logging in per request is what gets an IP blocked by Garmin. The client restores and refreshes saved tokens, uses credentials only when that fails, serialises logins, pauses 15 minutes after a failed login, and deletes dead tokens after 3 consecutive rejections so the next login is fresh. The library is blocking, so calls run in worker threads.
- **Thin tools, pure shaping.** Each tool is one file in `tools/`; payload shaping lives in `garmin/extract.py` (pure, unit-tested) and date handling in `garmin/dates.py`. Output is compact JSON text to keep phone context small.
- **Failures are `ToolError`s.** Any other exception reaches Claude only as "Error executing tool", so Garmin and input problems are raised as `GarminError` or `InvalidRequest` with a message safe to show.
- **No database.** The only runtime state is the Garmin token file in `data/`.

## Where things live

- `src/my_garmin_mcp/app.py`, `server.py`, `config.py` — ASGI app, MCP server, `.env` loading.
- `src/my_garmin_mcp/auth/` — key check, middleware, `rotate-key`.
- `src/my_garmin_mcp/garmin/` — `client.py`, `dates.py`, `extract.py`.
- `src/my_garmin_mcp/tools/` — one file per tool, wired in `tools/__init__.py`.
