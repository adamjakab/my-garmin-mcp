# Review 1 — Add MCP tool: all-day heart rate

**Verdict: PASS**

Scope: `fe4b7fda96d7e907ffade7a1beae2e399d65a7c2` (merge base with `main`) .. `6f9327e538fbb55d62d188595a2f43c5def5bb30` (branch tip). Frozen patch SHA-256 `37af05ae57997f3b46c9761746949036424209900c831cf90eeab3d55f4fa494`; SCOPE_ID `UP4TN-6f9327e-37af05ae`. Review reports excluded from the diff. The implementation report exists and its claims match the code: new `get_heart_rate` tool (`tools/heart_rate.py`), `heart_rate_day` in `garmin/extract.py`, `MAX_DAYS_HEART_RATE = 3`, version 0.4.0, docs updated. No scope creep found (the `AGENTS.md` update is documented in the report).

Coverage ledger: 8 source files, about 180 changed lines (larger than trivial), so all seven roles were dispatched as subagents (one dispatch each, no retries, none inline). CCA, CCB, DCS, CSS, EHS, DBS and TCS all returned `complete`. Not every role covered every path: DBS skipped the test files, `uv.lock` and the docs, and CCB only skimmed `extract.py` and the tests. Both are judged adequate for those roles. The patch hash was recomputed before consuming results and matched.

Note: `uv.lock` header `revision` changed 3 → 5 (uv version churn); it breaks no stated rule and the project's tests and lint pass.

## Checks

| Check | Command | Result |
|---|---|---|
| Install | `uv sync --locked` | exit 0 |
| Unit + e2e tests | `uv run pytest` | 39 passed |
| Lint | `uv run ruff check .` | All checks passed |
| Format | `uv run ruff format --check .` | 46 files already formatted |
| Type check | none declared by the project | not run (no checker configured) |

No check rewrote a tracked file; the tree stayed clean. There is no test database and none of these checks needed one.

## Candidates

| ID | Path:line | Category | Evidence | Confidence | Failure scenario | Baseline | Rule | Disposition |
|---|---|---|---|---|---|---|---|---|
| TCS-1 | tests/test_extract.py:135 | untested-branch | Malformed-pair/bool-bpm guards in `heart_rate_day` have no tests | 30 | Removing a guard leaves tests green | New function | none | rejected (below 75; speculative) |
| TCS-2 | tests/test_tools.py:142 | weak-assertion | Bucket validation tests assert only `is_error`; boundaries 5/120 not exercised | 25 | Off-by-one in range check unnoticed | New tool | none | rejected (below 75) |
| EHS-1 | src/my_garmin_mcp/garmin/extract.py:103 | error-propagation | Non-finite/huge timestamps or bpm raise OverflowError/ValueError, not ToolError | 25 | Garmin sends NaN/1e30 in `heartRateValues` and the call fails as "Error executing tool" | New code | "Failures must be `ToolError`s" | rejected (below 75; no reachable input shown from Garmin) |

CCA, CCB, DCS, CSS and DBS returned no candidates. Cross-check: for each candidate the strongest counter-evidence is that real Garmin payloads carry finite integer timestamps and bpm, and the behavior under test is covered by neighbouring tests; none reached the threshold. No `CHK` candidates, since every check passed.

## Findings

No issues found. Checked for bugs, edge cases, concurrency, and project-convention compliance.
