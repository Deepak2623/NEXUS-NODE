"""HITL router — human-in-the-loop approval/rejection endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from governance.auditor import log_audit_event

logger: structlog.BoundLogger = structlog.get_logger(__name__)
router = APIRouter(tags=["hitl"])

# ---------------------------------------------------------------------------
# HITL Decisions are now stored in the Supabase 'tasks' table 'status' column.
# 'hitl_wait' -> user triggers -> 'hitl_approved' or 'hitl_rejected'
# ---------------------------------------------------------------------------


class HITLDecision(BaseModel):
    """Request body for HITL approval/rejection."""

    actor: str = "user"
    reason: str = ""


@router.post("/hitl/{task_id}/approve")
async def approve_hitl(task_id: str, body: HITLDecision) -> dict[str, str]:
    """Approve a pending HITL gate for a task.

    Args:
        task_id: Task UUID awaiting HITL.
        body: Decision metadata.

    Returns:
        Acknowledgement dict.
    """
    logger.info("hitl_approved", task_id=task_id, actor=body.actor, reason=body.reason)
    await log_audit_event(
        task_id=task_id,
        node="HITL_PERMISSION_GRANTED",
        scrubbed_input={"decision": "approve", "actor": body.actor},
        scrubbed_output={"approved": True},
        pii_flags=[],
        actor=body.actor,
        hitl_event=True,
    )
    from stores.task_store import update_task_status
    await update_task_status(task_id, "hitl_approved")
    return {"task_id": task_id, "status": "approved"}


@router.post("/hitl/{task_id}/reject")
async def reject_hitl(task_id: str, body: HITLDecision) -> dict[str, str]:
    """Reject a pending HITL gate for a task.

    Args:
        task_id: Task UUID awaiting HITL.
        body: Decision metadata.

    Returns:
        Acknowledgement dict.
    """
    logger.info("hitl_rejected", task_id=task_id, actor=body.actor, reason=body.reason)
    await log_audit_event(
        task_id=task_id,
        node="HITL_PERMISSION_DENIED",
        scrubbed_input={"decision": "reject", "actor": body.actor},
        scrubbed_output={"approved": False},
        pii_flags=[],
        actor=body.actor,
        hitl_event=True,
    )
    from stores.task_store import update_task_status
    await update_task_status(task_id, "hitl_rejected")
    return {"task_id": task_id, "status": "rejected"}
