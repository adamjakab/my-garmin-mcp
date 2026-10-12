# Workspace boundaries

Write access is limited to this project folder, `my-garmin-mcp/`. Sibling projects (any folder next to this one) are read-only references.

## Rules

- **Read freely.** Inspect other projects to learn from them: their code, docs and decisions.
- **Never write outside `my-garmin-mcp/`.** No creating, editing, moving or deleting files in other projects, no `npm install` there, no git commands that change their state (commit, checkout, stash, etc.).
- **Do not run their tooling in place.** Builds, tests, dev servers and package managers write to disk (`node_modules`, `dist`, logs, lockfiles). If something needs running, copy what's needed into this project first.
- **Port, don't reference.** Anything worth keeping is copied into this project, in our own style. No imports, paths or scripts here may point at a sibling project.
- **Scratch files** go in the session scratchpad, not in a sibling project.

Notes about what was learned in a sibling belong in this project, e.g. under `docs/`.
