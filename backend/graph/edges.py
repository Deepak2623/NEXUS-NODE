"""Conditional edge routing for the NEXUS-NODE LangGraph mesh."""

from __future__ import annotations

import structlog

from graph.state import AgentState

logger: structlog.BoundLogger = structlog.get_logger(__name__)


def route_after_plan(state: AgentState) -> str:
    """Route from node_plan based on HITL and plan state.

    Args:
        state: Current agent state.

    Returns:
        Next node name.
    """
    if state.get("error"):
        return "END"
    if not state.get("tool_calls"):
        return "node_verify"
    return "node_execute"


def route_after_execute(state: AgentState) -> str:
    """Route from node_execute.
    
    Args:
        state: Current agent state.
        
    Returns:
        Next node name.
    """
    if state.get("error"):
        return "END"
    return "node_verify"


def route_after_verify(state: AgentState) -> str:
    """Route from node_verify: loop back or finish.

    Args:
        state: Current agent state.

    Returns:
        'node_plan' for replanning, 'END' for completion.
    """
    verification_result = state.get("verification_result", "complete")
    iteration_count = state.get("iteration_count", 0)

    logger.info(
        "routing_after_verify",
        verification_result=verification_result,
        iteration_count=iteration_count,
    )

    if verification_result == "needs_replanning":
        logger.info("restarting_cycle", task_id=state.get("task_id"))
        return "node_plan"
    
    logger.info("terminating_cycle", status=verification_result, task_id=state.get("task_id"))
    return "END"
