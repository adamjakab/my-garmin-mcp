# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Scaffolded: a minimal MCP server (Node >= 24, TypeScript, Express, `@modelcontextprotocol/server` v2 (`client` as a dev dependency, used by tests)) with one `ping` tool and API-key auth. Garmin integration is not started yet.

## Commands

- `npm run dev` - foreground server with file watching (`tsx watch`)
- `npm run server -- start|stop|restart|status|logs` - background server (pid/log in `.run/`); restart after code changes so the tool list refreshes
- `npm run keys -- create <name> | list | revoke <id|name>` - manage API keys (stored hashed in `data/keys.json`; plaintext shown once at creation)
- `npm run typecheck`, `npm test` (vitest, includes an end-to-end MCP client test), `npm run build` / `npm start`

Config via env: `PORT` (3334), `HOST` (127.0.0.1), `DATA_DIR` (`./data`).

## Architecture

- Streamable HTTP at `/mcp` via `createMcpHandler`, **stateless** (fresh server per request; small Express<->fetch bridge in `src/app.ts`), guarded by `Authorization: Bearer <key>`. `GET /health` is unauthenticated.
- `src/tools/` - one file per tool, registered in `src/tools/index.ts`.
- `src/auth/` - file-backed `KeyStore` (re-read on each call, so CLI changes apply without restart) and the bearer middleware.
- No database; runtime state lives in `data/` (gitignored).

## Connecting Claude Code to the local server

`claude mcp add --transport http my-garmin http://127.0.0.1:3334/mcp --header "Authorization: Bearer <key>"`

## Conventions

- [Workspace boundaries](docs/conventions/workspace-boundaries.md) - read sibling projects freely, write only inside `my-garmin-mcp/`.

## Purpose

A personal MCP (Model Context Protocol) server, written in Node.js + TypeScript, that lets the Claude mobile app talk to the owner's Garmin account. It fetches health data from Garmin and serves it back to Claude through MCP tools.

## Migration from legacy projects

The scaffold is meant to reuse code and knowledge from two existing sibling projects (to be identified by the user; likely candidates under `/home/jackisback/WslCode/garmin/` include `my-garmin-api`). Once this project is up and running, those two projects will be deleted, so anything worth keeping must be ported here rather than referenced in place. Do not add imports or paths pointing at the sibling projects.
