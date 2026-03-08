"""NEXUS-NODE AgentState definition — single source of truth for all graph state."""

from __future__ import annotations

import uuid
from typing import Annotated, Any, Optional

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class GovernanceRecord(BaseModel):
    """Immutable governance record attached to each state frame."""

    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    pii_flags: list[str] = Field(default_factory=list)
    input_hash: str = ""
    output_hash: str = ""
    hitl_event: bool = False
    actor: str = "system"


def add_governance_records(left: list[dict[str, Any]], right: list[dict[str, Any]] | dict[str, Any]) -> list[dict[str, Any]]:
    """Reducer to accumulate governance records instead of overwriting."""
    if isinstance(right, dict):
        return left + [right]
    return left + right


class AgentState(TypedDict):
    """Full LangGraph state for the NEXUS-NODE action mesh."""

    task_id: str
    task: str
    messages: Annotated[list[AnyMessage], add_messages]
    plan: list[str]
    current_step: int
    tool_calls: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    verification_result: Optional[str]
    status: str
    governance: dict[str, Any]  # Current node's governance metadata
    governance_records: Annotated[list[dict[str, Any]], add_governance_records]  # Historical audit log
    hitl_required: bool
    hitl_approved: Optional[bool]
    iteration_count: int
    context_docs: list[str]
    node_status: dict[str, str]   # node_name -> "pending"|"running"|"done"|"error"
    actor: str
    error: Optional[str]
