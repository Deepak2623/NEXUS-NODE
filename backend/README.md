# NEXUS-NODE — Backend API Reference

**FastAPI + LangGraph Action Mesh**  
Base URL: `http://localhost:8000/api/v1`

---

## 🔐 Authentication

All protected routes require a valid **RS256 JWT** in the `Authorization` header.

```bash
# Get a dev token (non-production only)
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"sub": "dev_user"}'
```

Use the returned `access_token` in all subsequent requests:

```bash
-H "Authorization: Bearer <access_token>"
```

---

## 🛰️ Endpoints

### Public / Analytics

| Method | Path          | Description                                  |
| :----- | :------------ | :------------------------------------------- |
| `GET`  | `/health`     | Returns server version, status, and UTC time |
| `POST` | `/auth/token` | Issues a dev JWT (disabled in production)    |

### Agentic Mesh Control

| Method   | Path                | Auth | Description                      |
| :------- | :------------------ | :--- | :------------------------------- |
| `POST`   | `/run`              | ✅   | Dispatch a new autonomous task   |
| `GET`    | `/stream/{task_id}` | ❌   | SSE stream of live graph events  |
| `GET`    | `/task/{task_id}`   | ✅   | Get single task snapshot from DB |
| `GET`    | `/tasks`            | ✅   | List recent mesh tasks           |
| `DELETE` | `/tasks/{task_id}`  | ✅   | Archive/Delete a specific task   |
| `DELETE` | `/tasks`            | ✅   | Purge task database              |

---

## 🧠 Graph Architecture (2026 Pattern)

NEXUS-NODE implements an **Agentic Retrieval** loop. The mesh does not rely on passive vector search; instead, it proactively fetches system state.

```
POST /run
  └── asyncio.Queue (SSE events)
        └── LangGraph Mesh (Cyclic)
              ├── node_plan    (Groq Llama-3.3-70b)
              │     └── @governed (PII scrub + HITL + Audit)
              ├── node_execute (MCP Tool Execution)
              │     └── @governed
              └── node_verify  (Groq Llama-3.1-8b)
                    └── @governed
                          └── Supabase Persistent Audit
```

---

## 🛠️ Environment Configuration

Set these in `backend/.env`. The system uses **Pydantic v2** for fail-fast startup validation.

| Variable               | Type   | Description                          |
| :--------------------- | :----- | :----------------------------------- |
| `GROQ_API_KEY`         | Secret | Inference for Plan/Verify nodes      |
| `GOOGLE_API_KEY`       | Secret | Multi-modal reasoning (Gemini Flash) |
| `SUPABASE_URL`         | URL    | Audit storage project URL            |
| `SUPABASE_SERVICE_KEY` | Secret | Backend service-role access          |
| `JWT_PRIVATE_KEY`      | Secret | RS256 signing key (Private)          |
| `JWT_PUBLIC_KEY`       | Plain  | RS256 verification key (Public)      |
| `ALLOWED_ORIGINS`      | List   | CORS whitelist                       |

---

## 🧪 Quality Assurance

```bash
# Unified test suite
uv run python -m pytest tests/ -v

# Integrity & Governance checks
uv run python -m pytest tests/test_governor.py -v
```

---

_Built for cryptographic trust and sub-300ms agentic reasoning._
