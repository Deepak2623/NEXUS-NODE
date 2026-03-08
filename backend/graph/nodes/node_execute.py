"""node_execute — tool dispatcher node."""

from __future__ import annotations

import structlog
from langchain_core.messages import AIMessage

from graph.nodes.governor import governed
from graph.state import AgentState
from tools.registry import TOOL_REGISTRY

logger: structlog.BoundLogger = structlog.get_logger(__name__)


@governed("node_execute")
async def node_execute(state: AgentState) -> dict:  # type: ignore[type-arg]
    """Execute queued tool calls from the plan node.

    Dispatches each tool call through the registry and collects results.

    Args:
        state: Current agent state with tool_calls populated.

    Returns:
        State delta with tool_results and updated messages.
    """
    task_id = state["task_id"]
    tool_calls: list[dict] = state.get("tool_calls", [])  # type: ignore[type-arg]
    results: list[dict] = []  # type: ignore[type-arg]

    if not tool_calls:
        logger.info("node_execute_no_tools", task_id=task_id)
        return {
            "tool_results": [],
            "node_status": {**state.get("node_status", {}), "node_execute": "done"},
        }

    for call in tool_calls:
        tool_name: str = call.get("name", "")
        tool_args: dict = call.get("args", {})  # type: ignore[type-arg]

        tool_fn = TOOL_REGISTRY.get(tool_name)
        if tool_fn is None:
            logger.warning("unknown_tool", task_id=task_id, tool=tool_name)
            results.append({"tool": tool_name, "error": f"Unknown tool: {tool_name}"})
            continue

        try:
            logger.info("executing_tool", task_id=task_id, tool=tool_name)
            result = await tool_fn(**tool_args)
            results.append({"tool": tool_name, "result": result})
        except Exception as exc:  # noqa: BLE001
            logger.error("tool_error", task_id=task_id, tool=tool_name, error=str(exc))
            results.append({"tool": tool_name, "error": str(exc)})

    summary = f"Executed {len(results)} tool(s): {[r['tool'] for r in results]}"

    return {
        "tool_results": results,
        "tool_calls": [],  # clear after execution
        "error": None,
        "status": "verifying",
        "current_step": state.get("current_step", 0) + 1,
        "messages": [AIMessage(content=summary)] if results else [],
        "node_status": {**state.get("node_status", {}), "node_execute": "done"},
    }
