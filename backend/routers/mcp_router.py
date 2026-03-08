"""MCP status router — health checks for GitHub, Slack, Salesforce."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter

from mcp.github_client import github_check_health
from mcp.salesforce_client import salesforce_check_health
from mcp.slack_client import slack_check_health

router = APIRouter(tags=["mcp"])


@router.get("/mcp/status")
async def mcp_status() -> dict[str, Any]:
    """Return live health status for all three MCP integrations.

    Returns:
        Dict with github, slack, salesforce health payloads.
    """
    github, slack, salesforce = await asyncio.gather(
        github_check_health(),
        slack_check_health(),
        salesforce_check_health(),
        return_exceptions=True,
    )

    def _safe(result: Any) -> dict[str, Any]:
        if isinstance(result, Exception):
            return {"status": "error", "error": str(result)}
        return result  # type: ignore[return-value]

    return {
        "github": _safe(github),
        "slack": _safe(slack),
        "salesforce": _safe(salesforce),
    }
