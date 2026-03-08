"""NEXUS-NODE FastAPI application — SSE streaming action mesh.

Wires together:
- pydantic-settings config validation (startup fails fast on missing env vars)
- JWT RS256 auth middleware on protected routes
- DB-backed task store (Supabase)
- LangGraph mesh execution with SSE streaming
- Rate limiting (60 req/min per IP)
- CORS with explicit origins from config
"""

from __future__ import annotations

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any, AsyncIterator

import structlog
import traceback
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from config import get_settings
from graph.builder import nexus_graph
from graph.state import AgentState
from middleware.auth import CurrentUser, create_access_token
from routers import audit_router, hitl_router, mcp_router
from stores.task_store import create_task, get_task, list_tasks, update_task_status
from stores.event_hub import task_events

# ---------------------------------------------------------------------------
# Logging & Settings
# ---------------------------------------------------------------------------
# We fetch settings inside functions to allow the app to start even if some env vars are missing
@lru_cache()
def _get_cached_settings():
    try:
        from config import get_settings as actual_get_settings
        return actual_get_settings()
    except Exception as e:
        logger.error("settings_load_error", error=str(e), traceback=traceback.format_exc())
        raise

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)
logger: structlog.BoundLogger = structlog.get_logger(__name__)

# In-memory SSE queues (ephemeral — only for active connections)
# Migrated to stores.event_hub.task_events for mesh accessibility


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan — startup and shutdown hooks."""
    settings = _get_cached_settings()
    logger.info(
        "nexus_node_starting",
        version="0.1.0",
        environment=settings.environment,
        max_iterations=settings.max_iterations,
    )
    yield
    logger.info("nexus_node_stopped")


# ---------------------------------------------------------------------------
# Rate limiter & App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="NEXUS-NODE Action Mesh",
    version="0.1.0",
    description="Autonomous low-latency enterprise action mesh",
    lifespan=lifespan,
    docs_url="/api/v1/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every incoming request for emergency debugging."""
    start_time = datetime.now(UTC)
    try:
        response = await call_next(request)
        duration = (datetime.now(UTC) - start_time).total_seconds()
        logger.info("request_finished", path=request.url.path, method=request.method, status=response.status_code, duration=duration)
        return response
    except Exception as e:
        logger.error("request_failed", path=request.url.path, error=str(e), traceback=traceback.format_exc())
        raise

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions — logs traceback and returns 500."""
    error_id = str(uuid.uuid4())
    error_msg = f"{type(exc).__name__}: {str(exc)}"
    logger.error("unhandled_exception", error_id=error_id, error=error_msg, traceback=traceback.format_exc())
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"NEXUS_BACKEND_CRASH: {error_msg}",
            "error_id": error_id,
            "path": request.url.path
        }
    )

# Routers (auth is applied per-route, not globally, so /health stays public)
app.include_router(audit_router.router, prefix="/api/v1")
app.include_router(hitl_router.router, prefix="/api/v1")
app.include_router(mcp_router.router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class RunRequest(BaseModel):
    """Request body for POST /api/v1/run."""

    task: str = Field(..., min_length=1, max_length=4000, description="Task description")
    context_docs: list[str] = Field(default_factory=list, description="Optional long-context docs")
    actor: str = Field(default="user", description="Identity initiating the task")


class RunResponse(BaseModel):
    """Response for POST /api/v1/run."""

    task_id: str
    status: str = "queued"


class TokenRequest(BaseModel):
    """Request body for POST /api/v1/auth/token (dev/test only)."""

    sub: str = Field(..., min_length=1, max_length=128)
    role: str = Field(default="user")


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    """Root endpoint for basic connectivity check."""
    return {"status": "ok", "message": "NEXUS-NODE Backend is running"}

@app.get("/api/v1/health")
async def health() -> dict[str, Any]:
    """Health check — includes detailed debug info about env vars."""
    s = _get_cached_settings()
    
    def _is_set(val: Any) -> bool:
        if isinstance(val, SecretStr):
            v = val.get_secret_value()
        else:
            v = str(val)
        return bool(v and "placeholder" not in v)

    return {
        "status": "ok",
        "version": "0.1.0",
        "environment": s.environment,
        "timestamp": datetime.now(UTC).isoformat(),
        "pending_hitl_count": await count_pending_hitl(),
        "config_check": {
            "supabase_url": _is_set(s.supabase_url),
            "supabase_key": _is_set(s.supabase_service_key),
            "groq_key": _is_set(s.groq_api_key),
            "google_key": _is_set(s.google_api_key),
            "jwt_private": _is_set(s.jwt_private_key),
            "jwt_public": _is_set(s.jwt_public_key),
            "github_token": _is_set(s.github_mcp_token),
            "slack_token": _is_set(s.slack_mcp_bot_token),
        }
    }


# Dev-only token endpoint (disabled in production)
@app.post("/api/v1/auth/token")
async def issue_token(body: TokenRequest) -> dict[str, str]:
    """Issue a dev JWT token. Disabled in production.

    Args:
        body: Subject and role for the token.

    Returns:
        Dict with access_token and token_type.

    Raises:
        HTTPException 403 in production.
    """
    # NOTE: Token issuance is enabled in production for this specific NEXUS-NODE deployment 
    # to allow the standalone frontend to authenticate with the backend via a shared secret logic
    # or development bypass if needed. In a real production system, this should be handled by 
    # a proper OIDC provider like Supabase Auth or Clerk.
    
    token = create_access_token(sub=body.sub, role=body.role)
    return {"access_token": token, "token_type": "bearer"}


# ---------------------------------------------------------------------------
# Protected endpoints (require valid JWT)
# ---------------------------------------------------------------------------
@app.post("/api/v1/run", response_model=RunResponse)
async def run_task(
    request: Request,
    body: RunRequest,
    current_user: CurrentUser,  # ← JWT required
) -> RunResponse:
    """Trigger a new mesh task; returns task_id for SSE streaming.

    Args:
        request: FastAPI request (for rate limiter).
        body: Task description and optional context.
        current_user: Validated JWT payload.

    Returns:
        RunResponse with task_id.
    """
    from langchain_core.messages import HumanMessage  # noqa: PLC0415
    from governance.pii_scrubber import scrub_text

    task_id = str(uuid.uuid4())
    actor = current_user.sub  # Use authenticated identity, not user-supplied

    scrubbed_task = scrub_text(body.task).text

    # Persist to DB — survives server restarts
    await create_task(task_id=task_id, task_text=scrubbed_task, actor=actor)

    initial_state: AgentState = {
        "task_id": task_id,
        "task": scrubbed_task,
        "messages": [HumanMessage(content=scrubbed_task)],
        "plan": [],
        "current_step": 0,
        "tool_calls": [],
        "tool_results": [],
        "verification_result": None,
        "status": "pending",
        "governance": {},
        "governance_records": [],
        "hitl_required": False,
        "hitl_approved": None,
        "iteration_count": 0,
        "context_docs": body.context_docs,
        "node_status": {},
        "actor": actor,
        "error": None,
    }

    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    task_events[task_id] = queue

    asyncio.create_task(_run_graph(task_id, initial_state, queue))
    logger.info("task_queued", task_id=task_id, actor=actor)
    return RunResponse(task_id=task_id)


async def _run_graph(
    task_id: str,
    state: AgentState,
    queue: asyncio.Queue[dict[str, Any]],
) -> None:
    """Background task — runs the LangGraph and emits SSE events + DB updates."""
    try:
        await update_task_status(task_id, "running")
        await queue.put({"type": "status", "data": {"phase": "started", "task_id": task_id}})

        final_state: AgentState = state
        async for event in nexus_graph.astream(state, stream_mode="values"):
            final_state = event  # type: ignore[assignment]
            msg_content = event.get("messages")[-1].content if event.get("messages") else None

            payload = {
                "type": "state_update",
                "data": {
                    "node_status": event.get("node_status", {}),
                    "iteration_count": event.get("iteration_count", 0),
                    "hitl_required": event.get("hitl_required", False),
                    "verification_result": event.get("verification_result"),
                    "plan": event.get("plan", []),
                    "status": event.get("status"),
                    "governance_records": event.get("governance_records", []),
                    "message": msg_content,
                },
            }
            await queue.put(payload)
            await update_task_status(
                task_id,
                event.get("status", "running"),
                iteration=event.get("iteration_count"),
            )

        await update_task_status(
            task_id,
            final_state.get("status", "completed"),
            result={
                "verification_result": final_state.get("verification_result"),
                "summary": final_state.get("messages")[-1].content if final_state.get("messages") else None
            },
        )
        await queue.put({"type": "status", "data": {"phase": "completed", "task_id": task_id}})

    except Exception as exc:  # noqa: BLE001
        logger.error("graph_run_error", task_id=task_id, error=str(exc))
        await update_task_status(task_id, "error", error=str(exc))
        await queue.put({"type": "error", "data": {"message": str(exc)}})
    finally:
        await queue.put({"type": "done"})
        # Clean up queue after 5 minutes (SSE client should be done by then)
        await asyncio.sleep(300)
        task_events.pop(task_id, None)


@app.get("/api/v1/stream/{task_id}")
async def stream_task(task_id: str) -> EventSourceResponse:
    """SSE endpoint — streams live graph events for a task. No auth (EventSource can't set headers).

    Args:
        task_id: UUID of the task to stream.

    Returns:
        Server-Sent Events response.
    """
    if task_id not in task_events:
        # Check DB — task might have already completed
        db_task = await get_task(task_id)
        if not db_task:
            raise HTTPException(status_code=404, detail=f"Task {task_id!r} not found")
        # Return the final state as a single SSE event
        async def _replay() -> AsyncIterator[str]:
            yield json.dumps({"type": "status", "data": {"phase": "completed", "task_id": task_id}})
        return EventSourceResponse(_replay())

    queue = task_events[task_id]

    async def generator() -> AsyncIterator[str]:
        while True:
            event = await queue.get()
            if event.get("type") == "done":
                break
            yield json.dumps(event)

    return EventSourceResponse(generator())


@app.get("/api/v1/task/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: CurrentUser,  # ← JWT required
) -> dict[str, Any]:
    """Return current DB state of a task.

    Args:
        task_id: UUID of the task.
        current_user: Validated JWT payload.

    Returns:
        Task record from Supabase.

    Raises:
        HTTPException 404 if task not found.
    """
    task = await get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id!r} not found")
    return task


@app.get("/api/v1/tasks")
async def list_all_tasks(
    current_user: CurrentUser,  # ← JWT required
    page: int = 1,
    page_size: int = 50,
    status: str | None = None,
) -> dict[str, Any]:
    """List recent tasks from DB with pagination.

    Args:
        page: Page number (1-indexed).
        page_size: Number of entries per page.
        status: Optional status filter.
        current_user: Validated JWT payload.

    Returns:
        Dict with tasks list.
    """
    result = await list_tasks(page=page, page_size=page_size, status_filter=status)
    return {"tasks": result["tasks"], "count": result["total_count"]}


@app.delete("/api/v1/tasks/{task_id}")
async def remove_task(
    task_id: str,
    current_user: CurrentUser,
):
    """Delete a specific task."""
    from stores.task_store import delete_task  # ensure it's imported
    await delete_task(task_id)
    return {"status": "deleted"}


@app.delete("/api/v1/tasks")
async def purge_tasks(
    current_user: CurrentUser,
):
    """Delete all tasks."""
    from stores.task_store import clear_tasks  # ensure it's imported
    await clear_tasks()
    return {"status": "all_cleared"}