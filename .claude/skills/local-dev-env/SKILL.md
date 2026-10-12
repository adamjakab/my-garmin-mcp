---
name: local-dev-env
description: How to start, stop, restart and check the local my-garmin-mcp dev server, and how to test it end to end through the Garmin-MCP-Local MCP tools. Use whenever the user asks how to start the development server, how to run or restart the MCP server locally, whether it is running, or how to test a tool after changing code.
---

# Local development environment

The dev server is a background process controlled by the script bundled with this skill, `scripts/server.sh` (relative to this skill's folder, so `.claude/skills/local-dev-env/scripts/server.sh` from the repo root). It works from any current directory, because it changes to the repo root itself. It starts `uv run python -m my_garmin_mcp` detached, records the pid in `.run/server.pid`, sends output to `.run/server.log`, and waits until `/health` answers before reporting success. There is no file watching, so a restart is how code changes are picked up. It listens on `http://127.0.0.1:3334/mcp` (`/health` is unauthenticated).

## Commands

- `.claude/skills/local-dev-env/scripts/server.sh start` - start in the background (pid and log live in `.run/`)
- `.claude/skills/local-dev-env/scripts/server.sh status` - running or stopped (exits non-zero when stopped, which is not an error)
- `.claude/skills/local-dev-env/scripts/server.sh restart` - restart; needed after any code or `.env` change, because the server loads code and `.env` once at startup
- `.claude/skills/local-dev-env/scripts/server.sh stop` - stop it (prints "not running" if it already was)
- `.claude/skills/local-dev-env/scripts/server.sh logs` - tail the server log
- `uv run python -m my_garmin_mcp` - foreground alternative, for the user's own terminal

Check `status` (or `curl -s localhost:3334/health`) before starting, so a second copy is never launched.

## Testing it yourself

Claude Code has this server registered as **Garmin-MCP-Local**. Once the server is up, its tools show up as `mcp__Garmin-MCP-Local__<tool>` (for example `ping`). They are deferred: load a tool's schema with ToolSearch (`select:mcp__Garmin-MCP-Local__ping`) before calling it.

So the end-to-end loop is: write or change a tool, `restart` the server, call the tool through `mcp__Garmin-MCP-Local__*`, and check the result. Prefer this over curl, since it goes through the real MCP client with the real access key.

**Reminder: after adding, removing or renaming a tool, the user has to refresh the MCP tool list manually** (the server's entry in the MCP configuration in VS Code, or `/mcp` to reconnect). Restarting the server is not enough, and Claude cannot do this from inside the session. So after a restart that changes the tool list, tell the user to refresh it and wait for their go-ahead before trying the new tool. A change inside an existing tool's handler needs only the restart.

If the tools are missing or fail after that, check `status` and `logs` first.

## When the user asks "how do I start it?"

Explain the commands above, mention that the tools can then be tested through Garmin-MCP-Local, and offer to start it. Don't start it unless asked to.
