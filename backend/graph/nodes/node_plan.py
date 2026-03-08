"""node_plan — Groq Llama-3.3-70b planner node."""

from __future__ import annotations

import json
import os
from typing import Any

import structlog
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from graph.nodes.governor import governed
from graph.state import AgentState

logger: structlog.BoundLogger = structlog.get_logger(__name__)

SYSTEM_PROMPT = """You are the NEXUS-NODE planner. Given a task, produce a concise JSON plan.

Output ONLY valid JSON in this exact schema:
{
  "plan": ["internal step 1", "internal step 2", "internal step 3"],
  "answer": "A friendly direct response to the user"
}

Constraints:
- Maximum 5 plan steps
- 🚨 **ANTI-HALLUCINATION**: NEVER assume or guess the outcome of a task that requires a tool (searching repos, querying accounts, etc). You MUST use the provided native function tools for operations you have not verified. Do NOT provide an affirmative/negative answer about data you haven't retrieved.
- Any write/delete operation (PR create, Slack post, SF update) must flag hitl_required=true in the state (though you only output the plan/answer JSON).
- If the required information is already present in the chat context or tool results, answer directly and do not schedule new tools.
- Check previous messages for 'Executed X tool' or 'Verification: complete' markers. If those exist, do NOT schedule the same tool again — simply confirm the result to the user using the 'answer' field.
- **General**: NEVER use placeholders like 'your_username', 'YOUR_OWNER', or 'example_org'. If you do not know the correct value, use search/list tools to find it or ask the user for clarification in the 'answer' field.
- **Salesforce**: DO NOT use 'SELECT *' in SOQL. Always specify fields. Valid Industries in this org include: 'Electronics', 'Biotechnology', 'Consulting', 'Energy', 'Education'. If 'Technology' yields no results, consider 'Electronics'.
- **Slack**: The bot currently lacks the 'channels:join' scope. You CANNOT use auto-join. You MUST ensure the bot is already in the channel or explain to the user why the post failed if 'not_in_channel' occurs. Known channels usually include '#general', '#random'.
"""

from config import get_settings
from tools.registry import TOOL_REGISTRY

import hashlib

PLAN_CACHE: dict[str, Any] = {}

@governed("node_plan")
async def node_plan(state: AgentState) -> dict[str, Any]:
    """LangGraph planner node backed by Groq Llama-3.3-70b.

    Args:
        state: Current agent state.

    Returns:
        State delta with updated plan and tool_calls.
    """
    settings = get_settings()
    logger.info("node_plan_key_check", key_len=len(settings.groq_api_key_str))
    
    messages = state.get("messages", [])
    task_id = state["task_id"]
    iteration_count = state.get("iteration_count", 0)

    # Simple in-memory Cache for identical initial Prompts
    cache_key = None
    if iteration_count == 0:
        last_user_msg = next((m.content for m in reversed(messages) if isinstance(m, HumanMessage)), None)
        if last_user_msg:
            cache_key = hashlib.sha256(str(last_user_msg).encode()).hexdigest()
            if cache_key in PLAN_CACHE:
                logger.info("node_plan_cache_hit", task_id=task_id, cache_key=cache_key)
                cached_data = PLAN_CACHE[cache_key]
                return {
                    "plan": cached_data.get("plan", []),
                    "tool_calls": cached_data.get("tool_calls", []),
                    "current_step": 0,
                    "status": "executing" if cached_data.get("tool_calls") else "verifying",
                    "messages": [AIMessage(content=cached_data.get("msg_text", "Using cached plan."))] if cached_data.get("msg_text") else [],
                    "node_status": {**state.get("node_status", {}), "node_plan": "done"},
                }

    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=settings.groq_api_key_str,
        temperature=0.1,
        max_tokens=2048,
        timeout=15.0,
    )

    chat_messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        *messages[-10:],  # keep last 10 for context window efficiency
    ]

    mcp_tools = list(TOOL_REGISTRY.values())
    llm_with_tools = llm.bind_tools(mcp_tools)

    logger.info("node_plan_invoking", task_id=task_id, msg_count=len(chat_messages))

    response = await llm_with_tools.ainvoke(chat_messages)
    content = response.content if isinstance(response.content, str) else str(response.content)

    # Parse structured JSON plan from Groq response
    plan: list[str] = []
    tool_calls: list[dict[str, Any]] = []
    answer: str | None = None
    
    # Pre-check for terminal errors in history to avoid loops
    last_verify_msg = next((m.content for m in reversed(messages) if "Verification:" in str(m.content)), "")
    if "missing_scope" in last_verify_msg or "Invite the bot" in last_verify_msg:
        logger.info("node_plan_terminal_error_detected", task_id=task_id)
        return {
            "plan": [],
            "tool_calls": [],
            "status": "completed",
            "messages": [AIMessage(content="I cannot proceed with the Slack post because the bot lacks the 'channels:join' scope. Please manually invite the 'nexus' bot to the channel and try again.")],
            "node_status": {**state.get("node_status", {}), "node_plan": "done"},
        }

    try:
        if content.strip():
            start_idx = content.find("{")
            end_idx = content.rfind("}")
            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx : end_idx + 1]
                parsed = json.loads(json_str)
                plan = parsed.get("plan", [])
                answer = parsed.get("answer")
            else:
                answer = content
    except (json.JSONDecodeError, ValueError, KeyError) as exc:
        logger.warning("node_plan_parse_error", task_id=task_id, error=str(exc))
        answer = content

    # Map native tool calls
    if hasattr(response, "tool_calls") and response.tool_calls:
        for tc in response.tool_calls:
            tool_calls.append({
                "name": tc["name"],
                "args": tc["args"]
            })

    # Finalise message content for the user
    if not tool_calls:
        msg_text = answer or (plan[0] if plan else content)
    else:
        msg_text = f"Plan: {plan}"

    if cache_key and iteration_count == 0:
        PLAN_CACHE[cache_key] = {
            "plan": plan,
            "tool_calls": tool_calls,
            "msg_text": msg_text
        }

    return {
        "plan": plan,
        "tool_calls": tool_calls,
        "current_step": 0,
        "status": "executing" if tool_calls else "verifying",
        "messages": [AIMessage(content=msg_text)],
        "node_status": {**state.get("node_status", {}), "node_plan": "done"},
    }
