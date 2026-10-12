# Legacy project reference: adam_mcp

Source (read-only): `/home/jackisback/WslCode/adibacsi/adam_mcp`
Purpose of this doc: let `my-garmin-mcp` (Node.js + TypeScript, personal MCP server for the Claude mobile app reading the owner's Garmin data) be scaffolded by porting pieces of adam_mcp, which will be deleted. All paths below are relative to the source project unless stated. Everything here was verified in the files; uncertain items are marked **(uncertain)**. Secrets found in `.env` are NOT reproduced.

---

## 1. Overview and tech stack

adam_mcp ("ADAM-MCP", package `adam-mcp` v1.0.2, author Adam Jakab, MIT) is a personal MCP server exposed over **Streamable HTTP** at `/mcp`, behind a self-hosted **OAuth 2.1 authorization server that delegates login to GitHub** (JWT access tokens, allowlist of GitHub user IDs). It was meant as a custom connector for Claude.

Tool sources (in the running server):

1. Built-in tools auto-discovered from the filesystem (ping, greeting, 8 mailbox IMAP/SMTP tools + 3 more, 6 JSON "memory store" tools).
2. **Dynamic tools generated at startup from remote OpenAPI specs** (`OPENAPI_TOOL_SOURCES`). The configured source is the author's own `my-garmin-api` (FastAPI) with prefix `garmin_` and an `x-api-key` header. **This is the Garmin integration: there are no hand-written Garmin tools in this repo.**
3. MCP resources: each memory store is exposed as `memory://<store>`.

| Item | Value |
| --- | --- |
| Language / module | TypeScript 6.0.x, `module: commonjs`, target ES2020, strict |
| Runtime | Node >= 24 (`engines`) |
| MCP SDK | `@modelcontextprotocol/sdk` ^1.29.0 (installed 1.29.0): high-level `McpServer` + `StreamableHTTPServerTransport` |
| Schemas | `zod` ^4.4.3, imported as `zod/v4` |
| HTTP | `express` ^5.2.1; `body-parser` is imported in `src/index.ts` but is NOT in package.json (only `@types/body-parser` in devDeps; works only via Express's transitive dep) |
| HTTP client | `axios` ^1.18.1 (OpenAPI proxy, spec loader, GitHub OAuth calls) |
| Config | `dotenv` ^17.4.2 |
| Auth libs | `jsonwebtoken` ^9.0.3 |
| Mail libs | `imap` ^0.8.19, `mailparser` ^3.9.12, `nodemailer` ^9.0.1 |
| Test | `jest` ^30, `ts-jest` ^29, `ts-node` ^10.9 |
| Lint | `eslint` ^10 flat config, `@typescript-eslint` ^8.62 |

Git: repo exists with history (last commit "feat(mailbox): add tools for email management and memory store operations"). `package-lock.json` present.

---

## 2. Directory map

```text
.env                              LIVE config incl. real secrets (gitignored). Do not copy values. No .env.example exists (README mentions one; it is absent).
.gitignore                        ignores node_modules, dist, .env*, resources/*.json (keeps *.schema.json), data/*.json, logs
.github/agents/tester.agent.md    Copilot-style "Tester" agent prompt (test/quality only). References `npm run type-check` which does NOT exist in package.json
README.md                         STALE structure section (mentions oauth/client.ts, token-store.ts, connectors/claude.ts, mcp/resources/index.ts that no longer exist); mailbox + auth sections are accurate except tool name (see 4.3)
package.json / package-lock.json
tsconfig.json                     rootDir ./src, outDir ./dist, resolveJsonModule (package.json is imported by server.ts), include src/**/*
jest.config.cjs                   ts-jest preset, node env, roots tests/, setupFiles tests/utils/setup-env.ts, clearMocks
eslint.config.cjs                 flat config; no-console warn (allows log/warn/error/info/debug); no-explicit-any off
resources/archive_actions.schema.json   memory-store schema (mailbox archive routing rules)
resources/email_spammers.schema.json    memory-store schema (spam sender list)
dist/                             STALE build output (contains files no longer in src, e.g. connectors/claude.js, oauth/client.js, mcp/tools/healthcheck.js, mailbox.js, memory/tools.js). Ignore; rebuild.
src/index.ts                      Express app bootstrap; mounts body parsers, oauthRouter, bearerAuth on /mcp, then initializeServer
src/config/env.ts                 All env parsing (OAuth, TTLs, allowlist, OPENAPI_TOOL_SOURCES, mailbox, STORE_PATH)
src/types/index.ts                Unused legacy interfaces (OAuthToken, User, MCPRequest, ...). Safe to drop.
src/mcp/server.ts                 McpServer factory, session map, /mcp handler (Streamable HTTP), idle sweeper, /health
src/mcp/tools/index.ts            registerTools(): calls auto-discovery
src/mcp/tools/discovery.ts        Filesystem auto-discovery + logging wrapper (REUSABLE)
src/mcp/tools/types.ts            ToolContext, ToolConfig, ToolHandler, ToolDefinition, ToolFactory
src/mcp/tools/ping.ts             tool `ping`
src/mcp/tools/greet-with-helobelo.ts   tool `greet-with-helobelo` (demo)
src/mcp/tools/mailbox/*.ts        mailbox tools + `_shared.ts` (IMAP helpers, spam/archive logic, 761 lines) + `index.ts` (re-exports 2 helpers for tests)
src/mcp/tools/memory/*.ts         memory tools + `_shared.ts` (store lookup context)
src/mcp/memory/{index,store,resources,types}.ts   JSON file-backed "memory store" engine + MCP resource registration
src/mcp/openapi/{index,loader,refs,register,types,zod-schema}.ts   OpenAPI 3.x -> MCP tool generator (REUSABLE, central to Garmin)
src/oauth/{router,middleware,jwt,store,github,github-token}.ts    entire auth stack (DROP/REPLACE)
tests/utils/setup-env.ts          sets fake env vars + temp STORE_PATH
tests/oauth/*.test.ts             8 files, ~94 tests, all auth
tests/mcp/openapi/openapi-utils.test.ts   4 tests (refs + zod conversion)
tests/mcp/tools/mailbox-*.test.ts         8 tests (archive rule + spam matcher pure functions)
```

Test counts are `it(`/`test(` occurrences (~131 total incl. 11 files). Tests were not executed during this documentation pass **(uncertain whether they pass)**.

---

## 3. MCP server setup

**Transport:** Streamable HTTP only (no stdio, no SSE). Single route `app.all("/mcp", ...)` registered in `initializeServer` (`src/mcp/server.ts`). Stateful: one `McpServer` + one `StreamableHTTPServerTransport` per client session.

**Bootstrap (`src/index.ts` -> `src/mcp/server.ts`):**

1. Express app; `json()` and `urlencoded({extended:false})` parsers.
2. `app.use(oauthRouter())` (public well-known/register/authorize/callback/token).
3. `app.use('/mcp', bearerAuth)` (JWT check) - runs before the `/mcp` handler.
4. `initializeServer(app)`: fetches OpenAPI specs (`loadOpenApiSources`), loads memory-store schemas (`loadAllStoreSchemas`), starts idle-session sweeper (15 min interval, `.unref()`), registers `/mcp` handler and `GET /health` (returns `{status:"ok"}`, unauthenticated since it is outside `/mcp`).
5. `app.listen(PORT)` (default 3334).

**Session handling (`server.ts`):**

- Sessions in an in-memory `Record<sessionId, {server, transport, lastActivityAt}>`.
- Request with known `mcp-session-id` header -> updates `lastActivityAt`, `transport.handleRequest(req,res,req.body)`.
- No session id + POST + `isInitializeRequest(body)` -> creates new `McpServer` (via `createMcpServer`), transport with `sessionIdGenerator: randomUUID`, stores session in `onsessioninitialized`, deletes it in `transport.onclose`, `server.connect(transport)`.
- Unknown session id -> HTTP 404 JSON-RPC error code -32001 "Session not found" (so client re-initializes). No session id on non-initialize -> 400, code -32000.
- Idle sweeper closes sessions idle > `SESSION_IDLE_TTL_HOURS` (default 360h = 15 days).
- Logs tool call name/args on `tools/call` (args logged at debug level; **beware logging of sensitive args in the new project**).
- Specs are fetched once at process start and reused for all sessions; a new `McpServer` per session re-registers all tools from the cached specs. Changing the Garmin API requires a restart.

**Server identity:** `McpServer({name: package.name, version, title: package.displayName, description}, {instructions: "Use this server to access Adam's tools, data and personal information."})`. Uses non-standard `displayName` field of package.json (resolved via `resolveJsonModule`).

**Registration mechanisms:**

- *Built-in tools*: `registerTools(server, {memoryStores})` -> `discoverAndRegisterTools(server, ctx, __dirname, ext)` (`src/mcp/tools/discovery.ts`). Recursively scans `src/mcp/tools` for files with the running extension (`.ts` under ts-node, `.js` built), skipping `index`, `types`, `discovery`, `*.d.ts` and any `_`-prefixed file. Tool name = relative path with separators replaced by `_` (`mailbox/list_folders.ts` -> `mailbox_list_folders`). Each module must `export const tool: ToolFactory = (ctx) => ({config, handler})`. Loaded with `require()` (commonjs-dependent). Handler is wrapped to log call args and elapsed ms and rethrow errors. Registered via `server.registerTool(name, config, handler)`. `config` = `{title, description, inputSchema (zod object or raw shape), outputSchema, annotations, _meta}`. Handlers return `{content:[{type:"text",text:JSON.stringify(x)}], structuredContent: x}` (errors: `isError:true`).
- *Dynamic tools*: `registerOpenApiTools(server, loadedSources)` (`src/mcp/openapi/register.ts`) - see section 4.4.
- *Resources*: `registerMemoryResources` (`src/mcp/memory/resources.ts`) uses `server.registerResource(name, "memory://<name>", {title, description, mimeType:"application/json"}, readCb)`.
- *Prompts*: none registered anywhere.

---

## 4. Tool, resource and prompt catalog

### 4.1 Built-in utility tools

| Name | File | Input | Output | Notes |
| --- | --- | --- | --- | --- |
| `ping` | `src/mcp/tools/ping.ts` | none | `{pong:true, timestamp:ISO}` (text + structuredContent) | readOnlyHint |
| `greet-with-helobelo` | `src/mcp/tools/greet-with-helobelo.ts` | `{name: string}` | text `"Helóbeló <name>! Hogy vagy?"` | demo; hyphenated name (filename-derived); drop |

### 4.2 Memory tools (JSON-file store; no external backend)

Engine: `src/mcp/memory/store.ts`. Schemas = `resources/*.schema.json` (fields: `name`, `type` string|number|boolean, `required`, `uniqueKey?`, `description?`). Data = `resources/<store>.json` (array of objects; gitignored; **resolved against `process.cwd()`**, so the process must run from project root). Validation (`validateEntry`) only checks required + primitive type. Writes are non-atomic `writeFileSync`. Store names are interpolated into each tool's `store_name` description at registration. Current stores: `archive_actions`, `email_spammers` (see section 8 on how mailbox tools use them). Shared helper: `src/mcp/tools/memory/_shared.ts`.

| Tool | File | Input | Output |
| --- | --- | --- | --- |
| `memory_list_stores` | `memory/list_stores.ts` | none | `{stores:[{name,description,fields}]}` |
| `memory_store_info` | `memory/store_info.ts` | `store_name: string` | `{name,description,fields[{name,type,required,uniqueKey,description}]}` |
| `memory_read_store` | `memory/read_store.ts` | `store_name` | `{store,count,entries}` |
| `memory_add_entry` | `memory/add_entry.ts` | `store_name`, `entry: record<string,unknown>` | `{store, added}`; error on unknown store, validation fail, duplicate uniqueKey |
| `memory_update_entry` | `memory/update_entry.ts` | `store_name`, `key_value: string \| number \| boolean`, `updates: record` | `{store, updated}`; needs a uniqueKey field; re-validates merged entry |
| `memory_remove_entry` | `memory/remove_entry.ts` | `store_name`, `key_value` | `{store, removed:{<key>:value}}`; destructiveHint |

Resources: `memory://archive_actions`, `memory://email_spammers` (JSON text of all entries, `application/json`).

### 4.3 Mailbox tools (IMAP + SMTP; env-configured, not Garmin-related)

All in `src/mcp/tools/mailbox/`, helpers in `_shared.ts` (`ensureMailboxConfig` throws listing missing env vars; `withImap` connect/close; move/flags/search/fetch; spam + archive rule matching; `capText` 12000 chars). Each call opens a fresh IMAP connection. Output format: JSON text + structuredContent. Tool names are derived from filenames: README lists `mailbox_archive_emails_by_received_year`, but the actual name is **`mailbox_archive_emails`**; README omits `mailbox_check_new_emails` and `mailbox_move_spammers_to_spam`.

| Tool | Input (zod) | Behaviour / output |
| --- | --- | --- |
| `mailbox_list_folders` | none | `{folders: string[], tree}`; readOnly |
| `mailbox_create_archive_folder` | `subpath: string(min1)` | creates under Archive only; `{created:true, archivePath}` |
| `mailbox_archive_emails` | `mailbox?: string`, `uids?: int>0[] (min1)` | archives per `archive_actions` rules else `Archive/<year>`; marks \Seen; `{sourceMailbox, archivedCount, rulesMatched, yearFallbacks, rulesConfigured, archivedByTarget[{targetMailbox,count,source}]}` |
| `mailbox_check_new_emails` | `{}` | runs spam cleanup on "Inbox" then lists inbox (all UIDs, newest first, no limit); `{spamCleanup, inbox:{mailbox,count,emails}}` |
| `mailbox_list_emails` | `limit?: int 1..500 (default 20)`, `mailbox?` | `{mailbox,count,emails[{uid,subject,from,to,date,flags}]}`; readOnly |
| `mailbox_move_emails` | `targetMailbox: string`, `uids: int>0[]`, `sourceMailbox?` | `{sourceMailbox,targetMailbox,movedCount,uids}` |
| `mailbox_move_spammers_to_spam` | `mailbox?`, `limit?: int 1..2000` | `{sourceMailbox,spamMailbox,scannedCount,matchedCount,movedCount,spamAddressesConfigured,moved[]}` |
| `mailbox_read_email` | `uid: int>0`, `mailbox?` | `{mailbox,uid,subject,from,to,date,messageId,flags,text,html}` (text/html capped); readOnly |
| `mailbox_reply_email` | `uid`, `body: string(min1)`, `html?`, `mailbox?` | sends via SMTP with In-Reply-To/References; `{mailbox,replyToUid,to,smtpMessageId,accepted,rejected}` |
| `mailbox_send_email` | `to: z.email()`, `subject`, `content`, `html?` | `{to,subject,smtpMessageId,accepted,rejected}` |

These are irrelevant to Garmin; port only if mail is wanted (probably not).

### 4.4 Dynamic OpenAPI tools (Garmin) - the relevant part

Configured by env `OPENAPI_TOOL_SOURCES` (JSON array). Live value (structure only; host redacted in this doc):

```json
[{"url":"https://<garmin-api-host>/openapi.json","namePrefix":"garmin_","headerEnvVars":{"x-api-key":"GARMIN_API_KEY"}}]
```

`OpenApiToolSource` (`src/mcp/openapi/types.ts`): `url`, `baseUrl?` (override of `servers[0].url`), `namePrefix?`, `headers?`, `headerEnvVars?` (header -> env var name), `timeoutMs?` (default 30000).

Resulting tools are generated from the sibling project `/home/jackisback/WslCode/garmin/my-garmin-api` (Python FastAPI; verified by reading its route files; its actual served OpenAPI was **not** fetched, so exact generated schemas are inferred). Tool name = `sanitize(prefix + operationId)`, max 64 chars, chars `[A-Za-z0-9_-]`:

| Generated tool | HTTP | Params (from my-garmin-api routes) |
| --- | --- | --- |
| `garmin_getSleepByDateRange` | GET /sleep | `start_date`, `end_date` (YYYY-MM-DD, required); 400 if end<start; 404 if none |
| `garmin_getHrvByDateRange` | GET /hrv | start_date, end_date |
| `garmin_getRhrByDateRange` | GET /rhr | start_date, end_date |
| `garmin_getVo2MaxByDateRange` | GET /vo2max | start_date, end_date |
| `garmin_getWeightByDateRange` | GET /weight | start_date, end_date |
| `garmin_getActivitiesByDateRange` | GET /activities | start_date, end_date + enrichment flags `details, splits, typed_splits, split_summaries, exercise_sets, hr_time_in_zones, power_time_in_zones, weather, gear` (each "Y"/"N", pattern `^[YyNn]$`, default N) |
| `garmin_getActivityById` | GET /activity/{activity_id} | path `activity_id: string` + enrichment flags `details, splits, typed_splits, split_summaries, exercise_sets, hr_time_in_zones, power_time_in_zones, weather, gear` (flags list partly read; **uncertain** if identical to /activities) |
| (`getHealth`, GET /) | | disabled in my-garmin-api ("will not be discovered"), no key required |

my-garmin-api auth: header `x-api-key` (`api_auth.py`, `APIKeyHeader`), applied to all routers except those with `REQUIRE_API_KEY = False`.

**How generated tools work** (`src/mcp/openapi/`):

- `loader.ts`: axios GET of spec (15 s timeout), requires an `openapi` string field; failures logged and the source skipped (server still starts).
- `register.ts` (775 lines): per path/method -> `compileOperation`:
  - description = summary + description + `HTTP <METHOD> <path>` (max 4000 chars).
  - Inputs: path-level + operation parameters (operation wins); cookies skipped; name collisions across locations get `<name>_<in>` suffix; each param schema -> zod via `openApiSchemaToZod`, `.describe(param.description)`, optional unless `required`.
  - JSON request body: if plain object with properties and no name collision, properties are expanded to top-level inputs; otherwise a single `body` (or `request_body`) field. Non-JSON bodies = raw string.
  - Output: `outputSchema` only if success response (200/201/202/204/first 2xx/default) is a JSON object schema with properties; wrapped `.passthrough()`.
  - Annotations from HTTP method: GET/HEAD/OPTIONS readOnly+idempotent; DELETE/PUT destructive+idempotent; PATCH/POST destructive; all `openWorldHint:true`; `title` = summary.
  - Auth: reads `security`/`securitySchemes` (apiKey in header/query; http -> `Authorization`) to know which headers to expect; values come ONLY from source config (`headers`, `headerEnvVars` -> `process.env`). Missing header only logs a warning.
  - Call: `axios.request` with `validateStatus: () => true`; result text = `HTTP <status> <statusText>\nContent-Type...\n\n<body>`, body truncated at 200,000 chars; `isError` = status >= 400; `structuredContent` = response JSON only if non-array object and status < 400. Network errors -> isError text.
- `refs.ts` (79 lines): local `#/...` $ref resolution (`deref`, `derefSchema`, `isRef`), cycle-safe (tested).
- `zod-schema.ts` (327 lines): OpenAPI 3.0/3.1 schema -> Zod v4: string (format email/uuid/uri/url, pattern, min/maxLength), integer/number bounds, boolean, null, arrays, objects (+additionalProperties passthrough), enum, anyOf/oneOf unions with FastAPI-style `anyOf [X, null]` -> nullable, allOf -> intersection, `nullable:true`, defaults, descriptions; unknown -> `z.unknown()`. `isObjectSchema` exported.
- Date params: no special handling; FastAPI `date` appears as `{type:string, format:date}` -> plain string (no regex), so date format is not validated client-side.

---

## 5. Authentication (current) and coupling

**What it does:** MCP-spec OAuth 2.1 authorization server, built in-process (`src/oauth/`), delegating end-user identity to a **GitHub OAuth App** (scope `read:user`). Flow: Claude discovers `/.well-known/oauth-protected-resource` -> `/.well-known/oauth-authorization-server` -> `POST /register` (RFC 7591 DCR) -> `GET /authorize` (PKCE S256 required) -> GitHub login -> `GET /oauth/callback` (checks GitHub numeric user id against `ALLOWED_GITHUB_USER_IDS`) -> `POST /token` (`authorization_code` + `refresh_token` grants, rotating opaque refresh tokens stored as sha256 hashes) -> HS256 JWT access token (iss `PUBLIC_BASE_URL`, aud `PUBLIC_BASE_URL/mcp`, claims `sub`=login, `github_id`, `scope`, `client_id`; TTL default 360 h). `bearerAuth` on `/mcp` verifies JWT, re-checks allowlist, calls `ensureFreshGitHubToken` (refreshes the stored GitHub token), sets `req.user`; failures -> 401 with `WWW-Authenticate: Bearer ... resource_metadata=...` / 403 / JSON-RPC -32002.

**Files (all droppable):**

- `src/oauth/router.ts` (635 lines): metadata, register, authorize, callback, token, refresh logic.
- `src/oauth/middleware.ts`: `bearerAuth` + Express `Request.user` global type augmentation.
- `src/oauth/jwt.ts`: sign/verify, refresh-token generate/hash.
- `src/oauth/store.ts`: in-memory maps (clients, pending requests, auth codes, refresh tokens, GitHub tokens) + optional JSON persistence (`STORE_PATH`, atomic tmp+rename).
- `src/oauth/github.ts`, `src/oauth/github-token.ts`: GitHub authorize URL, code/refresh exchange, user fetch, proactive refresh.
- `src/types/index.ts`: unused OAuth/User interfaces.
- `tests/oauth/*` (8 files) and `tests/utils/setup-env.ts` (GitHub/JWT/STORE_PATH env stubs).

**Coupling points outside `src/oauth/` (what must be edited on removal):**

1. `src/index.ts`: imports `oauthRouter`, `bearerAuth`, `ALLOWED_GITHUB_USER_IDS`; `app.use(oauthRouter())`, `app.use('/mcp', bearerAuth)`, and the startup log line printing the allowlist. Removing these three leaves a working unauthenticated server.
2. `src/config/env.ts`: `GITHUB_CLIENT_ID`/`GITHUB_CLIENT_SECRET` and `JWT_SECRET` are `requireEnv` (server will not start without them), plus `GITHUB_REDIRECT_URI`, `ACCESS_TOKEN_TTL_*`, `REFRESH_TOKEN_TTL_*`, `ALLOWED_GITHUB_USER_IDS`, `isUserAllowed`, `STORE_PATH`. Note `SESSION_IDLE_TTL_*` and `PUBLIC_BASE_URL` are used by non-auth code too (server.ts / logging) and may be kept.
3. `src/mcp/server.ts`: NOT coupled to auth (no use of `req.user`; every session shares the same backend credentials).
4. Tools: no tool reads `req.user`; tool handlers have no per-user context. `ToolContext` contains only `memoryStores`.
5. The Garmin upstream credential is a single static `x-api-key` from env (`GARMIN_API_KEY`), independent of the OAuth user.

**Implication for parameter-driven auth:** the proxy layer (`register.ts`, `resolveSourceHeaders`) currently injects headers from process env at registration time. To make credentials per-request (from client-supplied parameters/headers), the header resolution must move into the per-call handler (it is already computed per tool-registration closure, `sourceHeaders`, so it is a small change). Also note the MCP server is currently created per session, but `req` is not passed to handlers, so reading request headers in handlers needs the SDK's `extra.requestInfo`/`authInfo` handler argument **(uncertain: verify in SDK 1.29 types)**.

---

## 6. Config, scripts, build/run/test, deployment

**npm scripts:** `build` = `tsc`; `start` = `node dist/index.js`; `dev` = `ts-node src/index.ts`; `test` = `jest --silent`; `lint` = `eslint .`; `lint:fix`. No `type-check`, no coverage script.

**Env vars (from `src/config/env.ts`; `.env` has all of these, values redacted):**

| Var | Default / required | Used by |
| --- | --- | --- |
| `PORT` | 3334 | server |
| `PUBLIC_BASE_URL` | `http://localhost:<PORT>` | auth metadata, JWT iss/aud, logs |
| `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` | required | auth |
| `GITHUB_REDIRECT_URI` | in `.env`, but code ignores it and uses `${PUBLIC_BASE_URL}/oauth/callback` | auth |
| `JWT_SECRET` | required | auth |
| `ACCESS_TOKEN_TTL_HOURS`, `REFRESH_TOKEN_TTL_HOURS` | 360 | auth |
| `SESSION_IDLE_TTL_HOURS` | 360 | MCP session sweeper |
| `ALLOWED_GITHUB_USER_IDS` | comma list of positive ints; empty = locked down | auth |
| `STORE_PATH` | optional; relative paths resolved from project root | OAuth persistence |
| `OPENAPI_TOOL_SOURCES` | optional JSON array; invalid JSON/shape throws at start | OpenAPI tools |
| `GARMIN_API_KEY` | referenced by name from `headerEnvVars` | Garmin upstream header `x-api-key` |
| `MAILBOX_IMAP_{HOST,PORT=993,TLS=true,USER,PASSWORD,DEFAULT_BOX=INBOX}`, `MAILBOX_SMTP_{HOST,PORT=587,SECURE=false,USER,PASSWORD}`, `MAILBOX_FROM_NAME` | optional at start, validated per call | mailbox tools |

**Run:** `npm install`, create `.env`, `npm run dev` or `npm run build && npm start`. Must run with cwd = project root for `resources/` lookup (`process.cwd()`). Deployed behind a public HTTPS domain (README example `adam-mcp.adibadi.net`).

**Deployment:** No Dockerfile, docker-compose, CI workflow, Procfile or systemd unit exists in the repo. Only `.github/agents/tester.agent.md`. Actual deployment mechanism is unknown **(uncertain)**.

---

## 7. What to port / what to drop

### Port (for my-garmin-mcp)

| Piece | Path | Notes |
| --- | --- | --- |
| OpenAPI -> MCP tool generator | `src/mcp/openapi/{register,loader,refs,zod-schema,types,index}.ts` | Core value: gives Garmin tools without hand-writing schemas. Make header resolution per-call/param-driven. Consider fetching spec once and caching, or replacing with hand-written tools (section 9). |
| Tests for refs/zod | `tests/mcp/openapi/openapi-utils.test.ts` | Small; extend for register.ts (currently untested) |
| Tool auto-discovery + logging wrapper | `src/mcp/tools/discovery.ts`, `index.ts`, `types.ts` | Convention: file path -> tool name, `export const tool` factory. Uses `require` + `readdirSync` (fails under ESM and when bundled; adapt if switching to ESM). |
| Streamable HTTP session handling | `src/mcp/server.ts` | Per-session McpServer, 404/400 semantics, idle sweeper, `/health`. Strip tool-arg debug logging if args are sensitive. Consider `sessionIdGenerator: undefined` (stateless) for a simple personal server **(design option, not in legacy)**. |
| `ping` tool | `src/mcp/tools/ping.ts` | Good smoke-test tool. |
| Env parsing patterns | `src/config/env.ts` (`requireEnv`, `parseBooleanEnv`, `parseOpenApiToolSources`) | Keep generic parts only. |
| Tool-result convention | any tool | `content` text JSON + `structuredContent`, `isError:true` on failure, annotations (`readOnlyHint`). |
| Jest/ESLint/tsconfig baseline | `jest.config.cjs`, `eslint.config.cjs`, `tsconfig.json` | Reasonable starting points. |
| Garmin tool contract (documentation) | section 4.4 | Names, dates `YYYY-MM-DD`, Y/N enrichment flags. |
| Memory store engine | `src/mcp/memory/*`, `src/mcp/tools/memory/*`, `resources/*.schema.json` | Only if a personal-notes store is wanted; not required for Garmin. |

### Drop / replace

- Entire `src/oauth/`, `src/types/index.ts`, `tests/oauth/`, GitHub/JWT env vars, `bearerAuth`/`oauthRouter` mounts, `ALLOWED_GITHUB_USER_IDS` log line, `STORE_PATH`.
- Mailbox tools + `_shared.ts` + deps `imap`, `mailparser`, `nodemailer` (not Garmin).
- `greet-with-helobelo`, `dist/`, stale README sections, `.github/agents/tester.agent.md` (optional keep as idea).
- Replace: static env-based `GARMIN_API_KEY` header injection with whatever parameter-driven credential model the Claude client supplies (e.g., Garmin credentials/token or the my-garmin-api key per request).

---

## 8. Available vs. missing / incomplete

**Available and working-by-inspection:** Streamable HTTP server + sessions; auto-discovered tools; OpenAPI-driven tools incl. Garmin read endpoints; memory stores; mailbox tools; OAuth stack with extensive tests.

**Gaps / issues found:**

- No direct Garmin client in this repo: depends on a separately hosted `my-garmin-api` (Python FastAPI, sibling project `/home/jackisback/WslCode/garmin/my-garmin-api`) which itself wraps Garmin Connect. The new project must either call that API or reimplement a Garmin Connect client (e.g. a Node Garmin Connect library, none used here).
- No hand-written Garmin tools, no Garmin-specific tests, no Garmin-specific prompts/resources.
- `register.ts` (the largest, most important module) has no tests; only `refs`/`zod-schema` are tested.
- No prompts; resources only for memory stores.
- README stale (non-existent files; wrong tool name; `.env.example` missing).
- `body-parser` imported but undeclared dependency.
- `tester.agent.md` mentions missing `npm run type-check`.
- `dist/` stale and contains removed modules; it is gitignored.
- Only one TODO in code: `tests/oauth/oauth-authcode-and-registration.test.ts:723` (needs client deletion API).
- `GITHUB_REDIRECT_URI` env var is ignored (derived from `PUBLIC_BASE_URL`).
- `isError` for 4xx/5xx upstream responses also includes upstream body text in the result; no response size reduction beyond 200k-char cap (may be large for activity details with enrichments; Claude mobile context limits **(uncertain)**).
- `structuredContent` is passed through when an `outputSchema` exists; SDK validates it, so schema mismatches from the upstream could yield tool errors (the code comment says it avoids this, but still returns `obj` for object responses regardless of schema) **(risk, untested)**.
- Idle-session sweeper only closes sessions; if `server.close()` succeeds the transport `onclose` deletes the entry (not independently verified).
- Memory store writes are non-atomic and uncached; concurrent writes may corrupt.
- Session state in memory only; restart drops sessions (clients get 404 and re-init, which is the spec behaviour).
- Mailbox spam/archive logic: archive fallback skips messages with no date (they are silently left in place).

---

## 9. Open questions and risks

1. Which upstream will the new server call: the existing hosted `my-garmin-api` (and its `x-api-key`), or Garmin Connect directly? This decides whether `src/mcp/openapi/*` is the right port (generated tools) or hand-written tools are better (explicit, curated descriptions, summaries to fit mobile context).
2. Parameter-driven auth: how will the Claude client pass the credential (custom header on the connector URL, query parameter, tool parameter)? The generator currently takes secrets only from server env. Need to confirm handler access to request headers in SDK 1.29 (`extra.requestInfo`) **(uncertain)** and that the Claude mobile app can supply it.
3. Spec fetch at startup: if the Garmin API is down at boot, zero Garmin tools are registered (warning only); there is no retry/refresh.
4. Large payloads: `garmin_getActivityById`/`getActivitiesByDateRange` with all enrichment flags can be huge; consider default-trimming or summarizing for mobile.
5. Date handling: dates are unvalidated strings client-side; define range limits and timezone semantics.
6. Security: the legacy `.env` contains real secrets (GitHub OAuth secret, JWT secret, Garmin API key, mailbox passwords). They are gitignored but exist on disk; rotate them if this project/disk is shared, and do not copy `.env` into the new project.
7. CommonJS + `require`-based discovery will not work if the new project targets ESM (`type: module`) or bundling; decide early.
8. Unknown deployment target (no Docker/CI in source); new project needs its own HTTPS hosting (Claude mobile requires a reachable remote MCP URL).
9. Test status of the legacy suite not verified in this pass.
