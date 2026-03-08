"""node_verify — Groq Llama-3.1-8b reasoning and verification node."""

from __future__ import annotations

import json
import os
from typing import Any

import structlog
from langchain_core.messages import AIMessage, SystemMessage
from langchain_groq import ChatGroq

from graph.nodes.governor import governed
from graph.state import AgentState

logger: structlog.BoundLogger = structlog.get_logger(__name__)

VERIFY_SYSTEM = """You are the NEXUS-NODE absolute verifier. Your job is to strictly analyze the execution and prevent useless loops.

Respond ONLY with valid JSON:
{
    "status": "complete" | "needs_replanning" | "failed",
    "summary": "one-line summary of status",
    "issues": ["error message or gap"],
    "confidence": 0.0-1.0
}

🚨 TERMINAL FAILURE RULES (Status: "failed"):
1. If any tool reports 'missing_scope', 'invalid_auth', '403 Forbidden', 'invalid_client', or 'invalid_credentials'.
2. If the tool result says 'Invite the bot manually' or 'Bot lacks channels:join scope'.
3. If the tool result is a '404 Not Found' on a resource that definitely should exist or contains placeholders like 'your_username', 'YOUR_OWNER', etc.
4. If the same error has happened more than once for the same tool with the same arguments.
5. If the required data (e.g. repo, account) is confirmed NOT to exist after a search.

🔄 REPLANNING RULES (Status: "needs_replanning"):
1. Only replan if a fix is possible (e.g., trying a different valid industry name, or fetching a missing piece of info that IS accessible).
2. If the plan is partially done but more steps are needed to reach the goal.
3. If you can identify the correct parameters (e.g. correct repo name) from recent search tool results.

✅ COMPLETION RULES (Status: "complete"):
1. All user objectives were met.
2. The user just said hi or asked a general question with no tool needs.
3. The iteration limit or a safety break was mentioned in messages.
"""


from config import get_settings

@governed("node_verify")
async def node_verify(state: AgentState) -> dict[str, Any]:
    """LangGraph verification node backed by Groq Llama-3.1-8b.

    Analyses tool results and long-context docs for a holistic verdict.

    Args:
        state: Current agent state with tool_results populated.

    Returns:
        State delta with verification_result and updated messages.
    """
    settings = get_settings()
    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        api_key=settings.groq_api_key_str,
        temperature=0.0,
        max_tokens=1024,
        timeout=15.0,
    )

    task_id = state["task_id"]
    tool_results = state.get("tool_results", [])
    plan = state.get("plan", [])
    context_docs = state.get("context_docs", [])

    # Bypass Gemini for conversational replies with no tools
    if not tool_results and (not plan or all("tool_call" not in p.lower() for p in plan)):
        logger.info("node_verify_bypass_conversational", task_id=task_id)
        return {
            "verification_result": "complete",
            "status": "completed",
            "messages": [],
            "node_status": {**state.get("node_status", {}), "node_verify": "done"},
        }

    # Iteration Guard: If we are deep in a loop, force completion to prevent crash
    iteration_count = state.get("iteration_count", 0)
    if iteration_count >= 8:
        any_success = any("result" in r for r in tool_results)
        logger.warning("node_verify_loop_breaker_engaged", task_id=task_id, iteration=iteration_count)
        return {
            "verification_result": "complete",
            "status": "completed",
            "messages": [AIMessage(content="Verification safety break: task concluded due to max iterations.")],
            "node_status": {**state.get("node_status", {}), "node_verify": "done"},
        }

    # Build verification payload
    verify_payload = {
        "plan": plan,
        "executed_steps": state.get("current_step", 0),
        "tool_results": tool_results,
        "context_summary": context_docs[:3],   # first 3 docs for context budget
    }

    user_content = f"Verify the following execution:\n```json\n{json.dumps(verify_payload, indent=2)}\n```"

    chat_messages = [
        SystemMessage(content=VERIFY_SYSTEM),
        *state.get("messages", [])[-5:],  # last 5 messages
    ]

    logger.info("node_verify_invoking", task_id=task_id, tool_results_count=len(tool_results))

    response = await llm.ainvoke(chat_messages + [{"role": "user", "content": user_content}])
    content = response.content if isinstance(response.content, str) else str(response.content)

    # Parse verification JSON
    verification_status = "complete"
    try:
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        parsed = json.loads(content)
        verification_status = parsed.get("status", "complete")
    except (json.JSONDecodeError, IndexError):
        logger.warning("node_verify_parse_error", task_id=task_id)

    # Hard-coded check for Slack scope/join issues to break loops
    for res in tool_results:
        err = str(res.get("error", "")).lower()
        if "missing_scope" in err or "channels:join" in err or "invite the bot" in err:
            logger.info("node_verify_forcing_failed_status", task_id=task_id, reason="slack_permission")
            verification_status = "failed"
            content = json.dumps({
                "status": "failed",
                "summary": "Slack post failed: Bot lacks permissions to join channel.",
                "issues": ["The 'nexus' bot does not have 'channels:join' scope. You MUST manually invite the bot to the channel first."],
                "confidence": 1.0
            })
            break
        if "your_username" in err or "your_owner" in err:
            logger.info("node_verify_forcing_failed_status", task_id=task_id, reason="placeholder_detected")
            verification_status = "failed"
            content = json.dumps({
                "status": "failed",
                "summary": "Execution failed: Placeholder detected in tool calls.",
                "issues": ["The planner used a placeholder like 'your_username'. Please provide specific details or ensure the environment is configured correctly."],
                "confidence": 1.0
            })
            break

    return {
        "verification_result": verification_status,
        "status": "completed" if verification_status == "complete" else "planning",
        "messages": [AIMessage(content=f"Verification: {content}")],
        "node_status": {**state.get("node_status", {}), "node_verify": "done"},
    }
