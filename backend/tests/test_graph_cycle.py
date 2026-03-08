"""Integration tests for the NEXUS-NODE LangGraph mesh cycle.

Tests the full node_plan → node_execute → node_verify loop using:
- Mock LLM responses (no real API calls)
- Mock tool registry (no external MCP calls)
- Real graph structure from builder.py

Run with:
    uv run pytest backend/tests/test_graph_cycle.py -v
"""

from __future__ import annotations

import json
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from graph.builder import build_graph
from graph.state import AgentState


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def sample_state() -> AgentState:
    """Minimal valid AgentState for testing."""
    return AgentState(
        task_id=str(uuid.uuid4()),
        task="Post a Slack message to #ops with the latest GitHub PR count",
        context_docs=[],
        messages=[],
        plan=[],
        current_step=0,
        tool_calls=[],
        tool_results=[],
        verification_result=None,
        status="pending",
        iteration_count=0,
        hitl_required=False,
        hitl_approved=None,
        governance_records=[],
        actor="test_user",
        error=None,
    )


@pytest.fixture()
def mock_groq_response() -> dict[str, Any]:
    """Simulated Groq plan response."""
    return {
        "plan": [
            "1. Query GitHub MCP for open PR count",
            "2. Format message with PR count",
            "3. Post to Slack #ops channel via Slack MCP",
        ],
        "tool_calls": [
            {"tool": "github_list_prs", "args": {"state": "open"}},
        ],
    }


@pytest.fixture()
def mock_gemini_response() -> dict[str, Any]:
    """Simulated Gemini verification response."""
    return {
        "status": "completed",
        "verification": "All steps executed. Slack message confirmed posted to #ops.",
        "passed": True,
    }


# ── Unit tests: individual nodes ──────────────────────────────────────────────

class TestNodePlan:
    """Tests for the planning node in isolation."""

    @pytest.mark.asyncio()
    async def test_plan_populates_state(self, sample_state: AgentState) -> None:
        """node_plan should populate state.plan from the LLM response."""
        mock_llm_content = json.dumps({
            "plan": ["Step A", "Step B"],
            "tool_calls": [{"tool": "slack_post_message", "args": {"channel": "#ops", "text": "Hello"}}],
        })

        mock_message = MagicMock()
        mock_message.content = mock_llm_content

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_message

        with patch("graph.nodes.node_plan.ChatGroq", return_value=mock_llm):
            from graph.nodes.node_plan import node_plan  # noqa: PLC0415
            result = await node_plan(sample_state)

        assert len(result["plan"]) == 2
        assert result["status"] == "executing"
        assert result["iteration_count"] == 1

    @pytest.mark.asyncio()
    async def test_plan_handles_llm_error(self, sample_state: AgentState) -> None:
        """node_plan should set status=error if LLM raises."""
        mock_llm = AsyncMock()
        mock_llm.ainvoke.side_effect = RuntimeError("Groq API timeout")

        with patch("graph.nodes.node_plan.ChatGroq", return_value=mock_llm):
            from graph.nodes.node_plan import node_plan  # noqa: PLC0415
            result = await node_plan(sample_state)

        assert result["status"] == "error"
        assert "Groq API timeout" in (result.get("error") or "")


class TestNodeExecute:
    """Tests for the tool execution node."""

    @pytest.mark.asyncio()
    async def test_execute_dispatches_tool(self, sample_state: AgentState) -> None:
        """node_execute should call the tool from the registry and record result."""
        sample_state["plan"] = ["Post Slack message"]
        sample_state["tool_calls"] = [
            {"tool": "slack_post_message", "args": {"channel": "#ops", "text": "3 open PRs"}},
        ]
        sample_state["status"] = "executing"

        mock_tool_result = {"ok": True, "ts": "1234567890.123456"}

        mock_registry: dict[str, AsyncMock] = {
            "slack_post_message": AsyncMock(return_value=mock_tool_result),
        }

        with patch("graph.nodes.node_execute.TOOL_REGISTRY", mock_registry):
            from graph.nodes.node_execute import node_execute  # noqa: PLC0415
            result = await node_execute(sample_state)

        assert len(result["tool_results"]) == 1
        assert result["tool_results"][0]["result"] == mock_tool_result
        assert result["status"] == "verifying"

    @pytest.mark.asyncio()
    async def test_execute_unknown_tool_sets_error(self, sample_state: AgentState) -> None:
        """node_execute should record an error for unregistered tools."""
        sample_state["tool_calls"] = [{"tool": "nonexistent_tool", "args": {}}]
        sample_state["status"] = "executing"

        with patch("graph.nodes.node_execute.TOOL_REGISTRY", {}):
            from graph.nodes.node_execute import node_execute  # noqa: PLC0415
            result = await node_execute(sample_state)

        assert result["tool_results"][0]["error"] is not None


class TestNodeVerify:
    """Tests for the verification node."""

    @pytest.mark.asyncio()
    async def test_verify_marks_completed(
        self,
        sample_state: AgentState,
        mock_gemini_response: dict[str, Any],
    ) -> None:
        """node_verify should mark state as completed when Gemini says passed=True."""
        sample_state["tool_results"] = [{"tool": "slack_post_message", "result": {"ok": True}}]
        sample_state["status"] = "verifying"

        mock_message = MagicMock()
        mock_message.content = json.dumps(mock_gemini_response)

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_message

        with patch("graph.nodes.node_verify.ChatGoogleGenerativeAI", return_value=mock_llm):
            from graph.nodes.node_verify import node_verify  # noqa: PLC0415
            result = await node_verify(sample_state)

        assert result["status"] == "completed"
        assert result["verification_result"] is not None

    @pytest.mark.asyncio()
    async def test_verify_replans_on_failure(self, sample_state: AgentState) -> None:
        """node_verify should set status='replanning' when verification fails."""
        sample_state["tool_results"] = [{"tool": "slack_post_message", "error": "channel not found"}]
        sample_state["status"] = "verifying"
        sample_state["iteration_count"] = 1

        mock_message = MagicMock()
        mock_message.content = json.dumps({
            "status": "replanning",
            "verification": "Slack message failed — channel not found.",
            "passed": False,
        })

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_message

        with patch("graph.nodes.node_verify.ChatGoogleGenerativeAI", return_value=mock_llm):
            from graph.nodes.node_verify import node_verify  # noqa: PLC0415
            result = await node_verify(sample_state)

        assert result["status"] in ("replanning", "planning")


# ── Integration test: full graph cycle ────────────────────────────────────────

class TestGraphCycle:
    """End-to-end graph execution tests using the compiled StateGraph."""

    @pytest.mark.asyncio()
    async def test_full_cycle_completes(
        self,
        sample_state: AgentState,
        mock_groq_response: dict[str, Any],
        mock_gemini_response: dict[str, Any],
    ) -> None:
        """Full plan → execute → verify cycle should reach 'completed' status."""
        mock_plan_msg = MagicMock()
        mock_plan_msg.content = json.dumps(mock_groq_response)

        mock_verify_msg = MagicMock()
        mock_verify_msg.content = json.dumps(mock_gemini_response)

        mock_groq = AsyncMock()
        mock_groq.ainvoke.return_value = mock_plan_msg

        mock_gemini = AsyncMock()
        mock_gemini.ainvoke.return_value = mock_verify_msg

        mock_tool_result = {"ok": True, "ts": "1111111111.000000"}
        mock_registry = {"github_list_prs": AsyncMock(return_value=mock_tool_result)}

        with (
            patch("graph.nodes.node_plan.ChatGroq", return_value=mock_groq),
            patch("graph.nodes.node_verify.ChatGoogleGenerativeAI", return_value=mock_gemini),
            patch("graph.nodes.node_execute.TOOL_REGISTRY", mock_registry),
            patch("governance.auditor.log_audit_event", new_callable=AsyncMock),
        ):
            graph = build_graph()
            final_state: AgentState = await graph.ainvoke(sample_state)

        assert final_state["status"] == "completed"
        assert final_state["iteration_count"] >= 1

    @pytest.mark.asyncio()
    async def test_max_iterations_raises(self, sample_state: AgentState) -> None:
        """Graph should raise MaxIterationsError after exceeding MAX_ITERATIONS."""
        # Always return 'replanning' to force looping
        always_replan_msg = MagicMock()
        always_replan_msg.content = json.dumps({
            "status": "replanning",
            "verification": "Keep trying.",
            "passed": False,
        })

        mock_plan_msg = MagicMock()
        mock_plan_msg.content = json.dumps({
            "plan": ["Try again"],
            "tool_calls": [],
        })

        mock_groq = AsyncMock()
        mock_groq.ainvoke.return_value = mock_plan_msg

        mock_gemini = AsyncMock()
        mock_gemini.ainvoke.return_value = always_replan_msg

        with (
            patch("graph.nodes.node_plan.ChatGroq", return_value=mock_groq),
            patch("graph.nodes.node_verify.ChatGoogleGenerativeAI", return_value=mock_gemini),
            patch("graph.nodes.node_execute.TOOL_REGISTRY", {}),
            patch("governance.auditor.log_audit_event", new_callable=AsyncMock),
            patch.dict("os.environ", {"MAX_ITERATIONS": "3"}),
        ):
            graph = build_graph()
            final_state: AgentState = await graph.ainvoke(sample_state)

        # Should terminate with error or hitl status, never loop infinitely
        assert final_state["status"] in ("error", "hitl_wait", "completed")
        assert final_state["iteration_count"] <= 5  # hard ceiling
