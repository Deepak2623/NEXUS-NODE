"""SHA-256 auditor — computes canonical hashes and writes to Supabase audit_log."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any

import structlog

from governance.supabase_client import get_supabase_client

logger: structlog.BoundLogger = structlog.get_logger(__name__)


def compute_hash(payload: dict[str, Any]) -> str:
    """Compute SHA-256 hash of a canonical JSON payload.

    Args:
        payload: Dictionary to hash. Values are serialised with default=str.

    Returns:
        Lowercase hexadecimal SHA-256 digest string.
    """
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


async def log_audit_event(
    *,
    task_id: str,
    node: str,
    scrubbed_input: dict[str, Any],
    scrubbed_output: dict[str, Any],
    pii_flags: list[str],
    actor: str = "system",
    hitl_event: bool = False,
) -> str:
    """Write a governance record to Supabase audit_log.

    Args:
        task_id: Unique task identifier.
        node: Name of the LangGraph node that produced this record.
        scrubbed_input: PII-scrubbed input payload.
        scrubbed_output: PII-scrubbed output payload.
        pii_flags: List of PII type names detected.
        actor: Identity that triggered the action.
        hitl_event: Whether this entry represents a HITL decision.

    Returns:
        The SHA-256 hash of the combined input+output.

    Raises:
        RuntimeError: If Supabase write fails.
    """
    ts = datetime.now(UTC).isoformat()
    input_hash = compute_hash({"node": node, "input": scrubbed_input, "timestamp": ts})
    output_hash = compute_hash({"node": node, "output": scrubbed_output, "timestamp": ts})

    record = {
        "task_id": task_id,
        "node": node,
        "actor": actor,
        "input_hash": input_hash,
        "output_hash": output_hash,
        "pii_flags": pii_flags,
        "hitl_event": hitl_event,
    }

    try:
        client = get_supabase_client()
        response = client.table("audit_log").insert(record).execute()
        logger.info(
            "audit_logged",
            task_id=task_id,
            node=node,
            input_hash=input_hash,
            pii_flags=pii_flags,
        )
        _ = response  # suppress unused-variable lint
    except Exception as exc:
        logger.error("audit_log_failed", task_id=task_id, node=node, error=str(exc))
        raise RuntimeError(f"Audit log write failed: {exc}") from exc

    return input_hash
