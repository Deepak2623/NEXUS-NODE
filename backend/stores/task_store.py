"""DB-backed task store using Supabase.

Replaces the in-memory dict in main.py.
Tasks survive server restarts and are queryable across multiple processes.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import structlog

from governance.supabase_client import get_supabase_client

logger: structlog.BoundLogger = structlog.get_logger(__name__)

_TABLE = "tasks"


async def create_task(task_id: str, task_text: str, actor: str = "user") -> dict[str, Any]:
    """Insert a new task row with status='pending'.

    Args:
        task_id: UUID string for the task.
        task_text: The raw user-supplied task description (PII-scrubbed upstream).
        actor: Identifier of who triggered the task.

    Returns:
        The created task record as a dict.
    """
    client = get_supabase_client()
    row = {
        "id": task_id,
        "task_text": task_text,
        "actor": actor,
        "status": "pending",
    }
    result = client.table(_TABLE).insert(row).execute()
    logger.info("task_created", task_id=task_id, actor=actor)
    return result.data[0] if result.data else row


async def get_task(task_id: str) -> dict[str, Any] | None:
    """Fetch a task by ID.

    Args:
        task_id: UUID string for the task.

    Returns:
        Task record dict or None if not found.
    """
    client = get_supabase_client()
    result = client.table(_TABLE).select("*").eq("id", task_id).limit(1).execute()
    return result.data[0] if result.data else None


async def update_task_status(
    task_id: str,
    status: str,
    result: dict[str, Any] | None = None,
    error: str | None = None,
    iteration: int | None = None,
) -> None:
    """Update the status (and optionally result/error) of an existing task.

    Args:
        task_id: UUID string for the task.
        status: New status string (pending | running | completed | error | hitl_wait).
        result: Optional final result payload.
        error: Optional error message.
        iteration: Current iteration count.
    """
    client = get_supabase_client()
    patch: dict[str, Any] = {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}
    if result is not None:
        patch["result"] = result
    if error is not None:
        patch["error"] = error
    if iteration is not None:
        patch["iteration"] = iteration

    client.table(_TABLE).update(patch).eq("id", task_id).execute()
    logger.info("task_updated", task_id=task_id, status=status)


async def list_tasks(limit: int = 50, status_filter: str | None = None) -> list[dict[str, Any]]:
    """Return recent tasks, optionally filtered by status.

    Args:
        limit: Maximum number of tasks to return.
        status_filter: If set, filter to tasks with this status.

    Returns:
        List of task record dicts, ordered by created_at descending.
    """
    client = get_supabase_client()
    query = client.table(_TABLE).select("*").order("created_at", desc=True).limit(limit)
    if status_filter:
        query = query.eq("status", status_filter)
    result = query.execute()
    return result.data or []


async def delete_task(task_id: str) -> None:
    """Delete a specific task record.

    Args:
        task_id: UUID of the task to delete.
    """
    client = get_supabase_client()
    client.table(_TABLE).delete().eq("id", task_id).execute()
    logger.info("task_deleted", task_id=task_id)


async def clear_tasks() -> None:
    """Delete ALL task records from the database."""
    client = get_supabase_client()
    # In Supabase/PostgREST, we need a filter to delete. 'neq.0' is a common hack for 'all' if id exists.
    # Or just use an empty filter if the policy allows.
    client.table(_TABLE).delete().neq("status", "non_existent").execute()
    logger.warning("all_tasks_cleared")
