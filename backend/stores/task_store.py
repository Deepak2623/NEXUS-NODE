"""DB-backed task store using Supabase.

Replaces the in-memory dict in main.py.
Tasks survive server restarts and are queryable across multiple processes.
"""

from __future__ import annotations

import asyncio
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
    await asyncio.to_thread(client.table(_TABLE).insert(row).execute)
    logger.info("task_created", task_id=task_id, actor=actor)
    return row


async def get_task(task_id: str) -> dict[str, Any] | None:
    """Fetch a task by ID.

    Args:
        task_id: UUID string for the task.

    Returns:
        Task record dict or None if not found.
    """
    client = get_supabase_client()
    result = await asyncio.to_thread(
        client.table(_TABLE).select("*").eq("id", task_id).limit(1).execute
    )
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
        status: New status string (pending | running | completed | error | hitl_wait | hitl_approved | hitl_rejected).
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

    await asyncio.to_thread(client.table(_TABLE).update(patch).eq("id", task_id).execute)
    logger.info("task_updated", task_id=task_id, status=status)


async def list_tasks(page: int = 1, page_size: int = 50, status_filter: str | None = None) -> dict[str, Any]:
    """Return recent tasks with pagination and total count.

    Args:
        page: Page number (1-indexed).
        page_size: Number of entries per page.
        status_filter: If set, filter to tasks with this status.

    Returns:
        Dict with 'tasks' (list) and 'total_count' (int).
    """
    client = get_supabase_client()
    offset = (page - 1) * page_size
    query = client.table(_TABLE).select("*", count="exact").order("created_at", desc=True).range(offset, offset + page_size - 1)
    if status_filter:
        query = query.eq("status", status_filter)
    
    result = await asyncio.to_thread(query.execute)
    return {
        "tasks": result.data or [],
        "total_count": result.count or 0
    }


async def delete_task(task_id: str) -> None:
    """Delete a specific task record.

    Args:
        task_id: UUID of the task to delete.
    """
    client = get_supabase_client()
    await asyncio.to_thread(client.table(_TABLE).delete().eq("id", task_id).execute)
    logger.info("task_deleted", task_id=task_id)


async def clear_tasks() -> None:
    """Delete ALL task records and ALL audit logs from the database (Atomic Purge)."""
    client = get_supabase_client()
    # Wipe audit log first
    await asyncio.to_thread(client.table("audit_log").delete().neq("node", "non_existent").execute)
    # Wipe tasks
    await asyncio.to_thread(client.table(_TABLE).delete().neq("status", "non_existent").execute)
    logger.warning("all_governance_data_purged")


async def count_pending_hitl() -> int:
    """Count tasks currently waiting for human approval.

    Returns:
        Integer count of 'hitl_wait' tasks.
    """
    client = get_supabase_client()
    result = await asyncio.to_thread(
        client.table(_TABLE).select("id", count="exact").eq("status", "hitl_wait").execute
    )
    return result.count or 0
