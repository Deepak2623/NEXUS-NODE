"""GovernorNode — mandatory pre/post middleware for every LangGraph node.

Applies PII scrubbing and writes SHA-256 audit hashes before returning
any result to the graph. Provides the @governed decorator.
"""

from __future__ import annotations

import functools
import json
import os
import uuid
from datetime import UTC, datetime
from typing import Any, Callable, Coroutine, TypeVar

import structlog

from governance.auditor import log_audit_event
from governance.pii_scrubber import scrub_dict
from graph.state import AgentState

logger: structlog.BoundLogger = structlog.get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Coroutine[Any, Any, dict[str, Any]]])  # type: ignore[type-arg]

# Actions that require Human-in-the-Loop approval
HITL_ACTIONS: frozenset[str] = frozenset(
    [
        "git_push",
        "git_force_push",
        "file_delete",
        "dir_delete",
        "record_delete",
        "bulk_update",
        "slack_post_message",
        "github_create_pr",
        "salesforce_update_opportunity",
    ]
)


class MaxIterationsError(Exception):
    """Raised when the LangGraph cycle exceeds MAX_ITERATIONS."""


def governed(node_name: str) -> Callable[[F], F]:
    """Decorator factory that wraps a LangGraph node with governance middleware.

    Args:
        node_name: Human-readable node identifier used in audit records.

    Returns:
        Decorator that wraps the target async node function.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(state: AgentState, *args: Any, **kwargs: Any) -> dict[str, Any]:
            task_id = state.get("task_id", str(uuid.uuid4()))
            max_iter = int(os.environ.get("MAX_ITERATIONS", "10"))

            # Iteration guard
            iteration_count = state.get("iteration_count", 0)
            if iteration_count >= max_iter:
                logger.error(
                    "max_iterations_exceeded",
                    task_id=task_id,
                    node=node_name,
                    iteration_count=iteration_count,
                )
                raise MaxIterationsError(
                    f"Task {task_id} exceeded {max_iter} iterations in node '{node_name}'."
                )

            # --- PRE-PROCESSING ---
            raw_input: dict[str, Any] = {
                "task_id": task_id,
                "node": node_name,
                "messages_count": len(state.get("messages", [])),
                "current_step": state.get("current_step", 0),
                "tool_calls_pending": state.get("tool_calls", []),
            }
            scrubbed_input, input_flags = scrub_dict(raw_input)

            logger.info(
                "governor_pre",
                task_id=task_id,
                node=node_name,
                pii_flags=input_flags,
            )

            # HITL check on pending tool calls
            pending_tools: list[dict[str, Any]] = state.get("tool_calls", [])
            hitl_required = any(
                tc.get("name", "") in HITL_ACTIONS for tc in pending_tools
            )
            if hitl_required and not state.get("hitl_approved"):
                logger.warning(
                    "hitl_required",
                    task_id=task_id,
                    node=node_name,
                    actions=[tc.get("name") for tc in pending_tools if tc.get("name") in HITL_ACTIONS],
                )
                import asyncio
                # Import safely at runtime to avoid circular dependencies
                import main
                queue = main._task_events.get(task_id)
                if queue:
                    # Emit a synthetic event so the UI flips to HITL required
                    asyncio.create_task(queue.put({
                        "type": "state_update",
                        "data": {
                            "hitl_required": True,
                            "status": "hitl_wait",
                            "node_status": state.get("node_status", {}),
                            "message": "⚠️ Waiting for Human Approval on sensitive action..."
                        }
                    }))
                    asyncio.create_task(main.update_task_status(task_id, "hitl_wait"))

                from stores.task_store import get_task
                
                logger.warning("hitl_polling_started", task_id=task_id)
                # Max 600s wait (300 * 2s)
                for _ in range(300):
                    task_rec = await get_task(task_id)
                    if task_rec:
                        if task_rec.get("status") == "hitl_approved":
                            state["hitl_approved"] = True
                            break
                        if task_rec.get("status") == "hitl_rejected":
                            state["hitl_approved"] = False
                            break
                    await asyncio.sleep(2)
                
                if not state.get("hitl_approved"):
                    from langchain_core.messages import AIMessage
                    logger.error("hitl_rejected_or_timeout", task_id=task_id)
                    return {
                        "hitl_required": True,
                        "hitl_approved": False,
                        "status": "completed",
                        "error": "Task was REJECTED by human.",
                        "messages": [AIMessage(content="I cannot proceed; the requested action was rejected by the supervisor.")],
                        "node_status": {**state.get("node_status", {}), node_name: "done"}
                    }
                
                # If approved, hitl_approved is True, proceed to execute the node below

            # --- EXECUTE NODE ---
            result: dict[str, Any] = await func(state, *args, **kwargs)

            # --- POST-PROCESSING ---
            raw_output: dict[str, Any] = {
                k: v
                for k, v in result.items()
                if k not in ("messages",)  # skip large message lists for hashing
            }
            scrubbed_output, output_flags = scrub_dict(raw_output)
            all_flags = list(set(input_flags + output_flags))

            await log_audit_event(
                task_id=task_id,
                node=node_name,
                scrubbed_input=scrubbed_input,
                scrubbed_output=scrubbed_output,
                pii_flags=all_flags,
                hitl_event=hitl_required,
            )

            logger.info(
                "governor_post",
                task_id=task_id,
                node=node_name,
                pii_flags=all_flags,
            )

            # Merge governance metadata into result
            governance = state.get("governance", {})
            governance.update({"pii_flags": all_flags, "last_node": node_name})
            result["governance"] = governance
            result["iteration_count"] = iteration_count + 1
            
            # Append local audit trail for streaming
            result["governance_records"] = {
                "timestamp": datetime.now(UTC).isoformat(),
                "node": node_name,
                "pii_flags": all_flags,
                "hitl_event": hitl_required,
            }

            return result

        return wrapper  # type: ignore[return-value]

    return decorator
