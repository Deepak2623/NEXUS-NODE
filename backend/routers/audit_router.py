"""Audit log router — paginated read access to Supabase audit_log."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Query

from governance.supabase_client import get_supabase_client

router = APIRouter(tags=["audit"])


@router.get("/audit")
async def get_audit_log(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    task_id: str | None = None,
) -> dict[str, Any]:
    """Return paginated audit log entries.

    Args:
        page: Page number (1-indexed).
        page_size: Number of entries per page.
        task_id: Optional filter by task_id.

    Returns:
        Paginated audit entries.
    """
    client = get_supabase_client()
    offset = (page - 1) * page_size
    query = (
        client.table("audit_log")
        .select("*", count="exact")
        .order("created_at", desc=True)
        .range(offset, offset + page_size - 1)
    )
    if task_id:
        query = query.eq("task_id", task_id)
    response = await asyncio.to_thread(query.execute)
    return {
        "page": page,
        "page_size": page_size,
        "entries": response.data,
        "count": response.count or 0
    }


@router.delete("/audit")
async def purge_audit_chain():
    """Wipe the entire audit chain."""
    from stores.task_store import clear_audit_log
    await clear_audit_log()
    return {"status": "audit_chain_purged"}
