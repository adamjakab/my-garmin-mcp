# Versioning

> Last updated: 2026-10-12

How the version is kept consistent, so a deployed build can be identified.

- The version lives in two places: `version` in `pyproject.toml` and `__version__` in `src/my_garmin_mcp/__init__.py`. A test fails if they differ.
- After a bump run `uv lock`, because the production install uses `--locked` and fails on a stale `uv.lock`.
- The `ping` tool reports the version, which is how to confirm what is deployed.
