# my-garmin-mcp

A personal MCP server (Python) that lets Claude, including the mobile app, read the owner's Garmin data through a handful of tools. See [docs/](docs/) for how it works and how to run it.

## Documentation

- [Architecture](docs/architecture/README.md) — how the server is built and why: transport, auth, the shared Garmin session, tool design.
- [Setup](docs/setup/README.md) — from clone to a running local server, configuration and tests.
- [Deployment](docs/deployment/README.md) — how it ships and runs in production (PM2, NGINX, updates).
- [Conventions](docs/conventions/README.md) — rules for working in this repo: versioning, workspace boundaries, documentation.

## License

MIT, see [LICENSE](LICENSE).
