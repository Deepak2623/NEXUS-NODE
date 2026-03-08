from __future__ import annotations
import asyncio
from typing import Any
from mcp.github_client import github_check_health
from mcp.salesforce_client import salesforce_check_health
from mcp.slack_client import slack_check_health
import structlog

logger: structlog.BoundLogger = structlog.get_logger(__name__)

async def check_mcp_integrations_health() -> dict[str, Any]:
    """Check the health status of all MCP integrations (GitHub, Slack, Salesforce).
    
    Returns a dictionary summarizing the operational status of each connected system.
    """
    logger.info("checking_all_mcp_health")
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
