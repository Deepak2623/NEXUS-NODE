# GEMINI.md — NEXUS-NODE Code-Style & Security Rules

> These rules are enforced across the entire NEXUS-NODE workspace.
> Antigravity agents MUST follow these constraints at all times.

---

## 1. Code Style

### Python (backend/)

- **Python version**: 3.12+
- **Package manager**: `uv` exclusively (no `pip install` directly)
- **Formatter**: `ruff format` (line length 100)
- **Linter**: `ruff check` (rules: E, F, I, N, UP, S, B, A, C4, PTH)
- **Type checker**: `mypy --strict`
- **Docstrings**: Google-style, required on all public functions/classes
- **Async**: All I/O operations must be `async`; no blocking calls in async context
- **Imports**: Sorted by `ruff`; stdlib → third-party → local, separated by blank lines
- **Naming**: `snake_case` for variables/functions, `PascalCase` for classes, `UPPER_SNAKE` for module-level constants
- **Error handling**: Explicit typed exceptions; no bare `except:`; all errors logged before re-raising
- **Test coverage**: ≥ 80% minimum; `pytest` with `pytest-asyncio`

### TypeScript (frontend/)

- **Framework**: Next.js 15.2 App Router with Turbopack
- **TypeScript**: Strict mode enabled (`"strict": true` in `tsconfig.json`)
- **Formatter**: Prettier (single quotes, 2-space indent, trailing commas)
- **Linter**: ESLint with `next/core-web-vitals` + `@typescript-eslint/strict`
- **Component style**: Functional components only; no class components
- **State**: Prefer React Server Components; use `useState`/`useReducer` minimally on client
- **Imports**: Absolute paths via `@/` alias; no relative `../../` imports beyond 1 level
- **Naming**: `PascalCase` for components, `camelCase` for vars/functions, `UPPER_SNAKE` for constants
- **CSS**: Tailwind CSS utility classes; no inline `style={}` props except for dynamic values
- **Accessibility**: All interactive elements must have `aria-label`; images must have `alt`

---

## 2. Security Rules

### Secrets Management

- **NEVER hardcode** API keys, tokens, passwords, or connection strings in source code
- All secrets are loaded exclusively from environment variables via `python-dotenv` (backend) or `process.env` (frontend)
- `.env` files are **gitignored**; only `.env.example` with placeholder values is committed
- Rotate all credentials immediately if accidentally committed; force-push and alert security@

### Input Validation

- All FastAPI endpoints use **Pydantic v2 models** for request validation; no raw `dict` inputs
- All user-facing inputs are validated on both client (Zod) and server (Pydantic)
- SQL: Use Supabase client parameterized queries **only**; no string interpolation in queries
- File paths: Whitelist-based validation; reject any `..` traversal sequences

### PII Handling

- The **GovernorNode MUST run** before every tool call and after every tool result
- PII scrubbing applies to: SSN, email addresses, credit card numbers, phone numbers, IP addresses
- Scrubbed values are replaced with `[REDACTED:<type>]` markers
- Original (pre-scrub) values are **never logged** anywhere
- PII detection uses compiled regex patterns from `governance/pii_scrubber.py`

### Audit Trail

- Every node invocation (node_plan, node_execute, node_verify, governor) generates a SHA-256 hash
- Hash input: `json.dumps({"node": node_name, "input": scrubbed_input, "timestamp": iso_utc}, sort_keys=True)`
- Hashes are written to the Supabase `audit_log` table synchronously before node result is returned
- No audit log entry may be deleted or modified; the table uses Row-Level Security (RLS) with insert-only policy

### Human-in-the-Loop (HITL)

- **Terminal policy: Agent-Assisted**
- The following actions REQUIRE explicit human approval before execution:
  - Any `git push` (including force push)
  - Any file or directory deletion (`rm`, `rmdir`, `shutil.rmtree`)
  - Any database record deletion or bulk update
  - Any Salesforce record mutation affecting > 10 records
- HITL requests time out after **600 seconds** and default to **reject**
- Approval events are logged to `audit_log` with `hitl_event = TRUE`

### Network & API Security

- FastAPI: Enable `CORSMiddleware` with explicit `allowed_origins` from env (no wildcards in production)
- Rate limiting: 60 req/min per IP on all `/api/*` endpoints via `slowapi`
- JWT: RS256 algorithm; tokens expire in 1 hour; refresh tokens stored in httpOnly cookies
- All external HTTP calls (MCP clients) must use `httpx.AsyncClient` with a 10s timeout
- TLS: All production endpoints MUST use HTTPS; reject HTTP connections

### MCP Protocol Security

- MCP tokens scoped to minimum required permissions (principle of least privilege)
- GitHub MCP: read-only scopes for non-HITL actions; `repo:write` only granted after HITL approval
- Slack MCP: `chat:write` and `channels:read` only; no admin scopes
- Salesforce MCP: API-only user with explicit object-level permissions

### Dependency Security

- Run `uv sync --frozen` in CI to prevent dependency drift
- Run `pip-audit` on every PR to detect known CVEs
- Pin all dependencies with exact versions in `pyproject.toml` and `package.json`
- No dependencies with known critical CVEs may be merged

---

## 3. Architecture Rules

### LangGraph Mesh

- All agent logic lives inside `graph/nodes/`; no agent logic in FastAPI route handlers
- The `GovernorNode` MUST be applied as a wrapper around **every** node function using the `@governed` decorator
- Maximum cycle iterations: 10 (configurable via `MAX_ITERATIONS` env var); raise `MaxIterationsError` if exceeded
- State mutations only through LangGraph reducers; no direct state dictionary mutation

### FastAPI

- All routes are prefixed with `/api/v1/`
- Use `APIRouter` for modular route organization; no routes defined in `main.py` directly
- Background tasks (`BackgroundTasks`) are used for SSE streaming; do not block the event loop
- Health endpoint: `GET /api/v1/health` returns `{"status": "ok", "version": "...", "timestamp": "..."}`

### Frontend

- Server Components fetch data; Client Components handle interaction only
- SSE connections use the custom `lib/sse.ts` hook; no raw `EventSource` usage elsewhere
- All API calls go through `lib/api.ts`; no `fetch()` calls in components directly
- Environment variables exposed to browser must be prefixed `NEXT_PUBLIC_`

---

## 4. Git Workflow

- Branch naming: `feat/<ticket>-<slug>`, `fix/<ticket>-<slug>`, `chore/<slug>`
- Commit messages: Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`)
- **No direct pushes to `main`**; all changes via PR with at least 1 approval
- PR title must reference a ticket: `[NEXUS-42] feat: add governor PII scrubber`
- **HITL required for all `git push` operations** — this is enforced by the GovernorNode

---

## 5. Observability

- Structured logging: `structlog` (backend), all log entries include `task_id`, `node`, `timestamp`
- Log level: `INFO` in production, `DEBUG` in development (set via `LOG_LEVEL` env var)
- Metrics: Expose Prometheus metrics at `/metrics` (latency histograms per node, error counters)
- Tracing: OpenTelemetry with OTLP exporter; trace every LangGraph cycle end-to-end

---

_Last updated: 2026-02-27 by Antigravity Lead Systems Architect_
