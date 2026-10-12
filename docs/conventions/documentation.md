# Documentation conventions

> Last updated: 2026-10-12

How the docs are organised, so they stay easy to navigate and trust.

- Layers: `AGENTS.md` stays thin, the root `README.md` has a Documentation section listing the areas under `docs/`, each area folder has its own `README.md` indexing its docs. Nothing deeper than that.
- Docs hold the why (decisions, constraints, shape). The code holds the what, so do not restate it.
- Every doc starts with a title and a `> Last updated: YYYY-MM-DD` line, and its entry in the area index carries a link, a "read this when..." hint and the same date.
- Amend an existing doc before creating a new one. Adding, moving or removing a doc updates its area index in the same change.
- Rejected approaches and open questions are not docs. Ideas for later go in `work/future-improvements.md`.
- Keep real hostnames, paths and secrets out of the docs; the repo may go public.
