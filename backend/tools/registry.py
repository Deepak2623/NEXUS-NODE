"""Tool registry — maps tool names to async callables."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from mcp.github_client import github_create_pr, github_get_file_content, github_get_repo
from mcp.salesforce_client import salesforce_query_accounts, salesforce_update_opportunity, salesforce_describe_object
from mcp.slack_client import slack_archive_channel, slack_list_channels, slack_post_message
from mcp.health import check_mcp_integrations_health

ToolFn = Callable[..., Coroutine[Any, Any, dict[str, Any]]]

TOOL_REGISTRY: dict[str, ToolFn] = {
    # GitHub MCP tools
    "github_get_repo": github_get_repo,
    "github_get_file_content": github_get_file_content,
    "github_create_pr": github_create_pr,
    # Slack MCP tools
    "slack_post_message": slack_post_message,
    "slack_list_channels": slack_list_channels,
    "slack_archive_channel": slack_archive_channel,
    # Salesforce MCP tools
    "salesforce_query_accounts": salesforce_query_accounts,
    "salesforce_update_opportunity": salesforce_update_opportunity,
    "salesforce_describe_object": salesforce_describe_object,
    # System Check tools
    "check_mcp_integrations_health": check_mcp_integrations_health,
}

__all__ = ["TOOL_REGISTRY"]
