# Local setup and run

> Last updated: 2026-10-12

From clone to a running dev server, and how to check it.

## Steps

1. Install [uv](https://docs.astral.sh/uv/) (Python 3.12 or later is required) and run `uv sync`.
2. Copy `.env.example` to `.env` (gitignored) and fill in the Garmin account. Generate the access key with `uv run rotate-key`. The variables are documented in `.env.example`; real environment variables override the file.
3. Start the server: `uv run python -m my_garmin_mcp` in the foreground, or `.claude/skills/local-dev-env/scripts/server.sh start|stop|restart|status|logs` in the background (pid and log in `.run/`). The server loads code and `.env` once, so restart after changes.
4. Check it: `curl -s localhost:3334/health`.
5. Connect Claude Code: `claude mcp add --transport http my-garmin http://127.0.0.1:3334/mcp --header "Authorization: Bearer <key>"`.

## Garmin login

The first Garmin call logs in with the credentials and saves tokens under `GARMIN_TOKEN_STORE`; later calls reuse them. Accounts that ask for MFA are not supported yet.

## Tests and lint

- `uv run pytest` (includes an end-to-end MCP client test)
- `uv run ruff check .` and `uv run ruff format .`

`.claude/skills/local-dev-env/scripts/server.sh` is for local development only; production is covered in [Deployment](../deployment/README.md).
