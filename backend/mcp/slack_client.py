"""Slack MCP connector — wraps Slack Web API via httpx."""

from __future__ import annotations

import os
from typing import Any

import httpx
import structlog
from config import get_settings

logger: structlog.BoundLogger = structlog.get_logger(__name__)

_BASE_URL = "https://slack.com/api"
_TIMEOUT = 10.0


def _headers() -> dict[str, str]:
    settings = get_settings()
    token = settings.slack_mcp_bot_token.get_secret_value()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


async def _resolve_channel_id(client: httpx.AsyncClient, name_or_id: str) -> str:
    """Resolve a channel name (like #general) to a channel ID (like C01234)."""
    # If it already looks like an ID, return it
    if name_or_id.startswith(("C", "D", "G")):
        return name_or_id
    
    clean_name = name_or_id.lstrip("#").lower()
    
    params = {"limit": 1000, "exclude_archived": "true", "types": "public_channel,private_channel"}
    resp = await client.get(f"{_BASE_URL}/conversations.list", headers=_headers(), params=params)
    if resp.status_code == 200:
        data = resp.json()
        for chan in data.get("channels", []):
            if chan["name"].lower() == clean_name:
                return str(chan["id"])
                
    return name_or_id # fallback


async def slack_post_message(
    *,
    channel: str,
    text: str | None = None,
    message: str | None = None,
    thread_ts: str | None = None,
) -> dict[str, Any]:
    """Post a message to a Slack channel with auto-resolution and auto-join.

    Args:
        channel: Channel ID or name (e.g. #general).
        text: Message text.
        message: Alias for text.
        thread_ts: Optional thread ts.

    Returns:
        Slack response.
    """
    body_text = text or message or ""
    
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        # Resolve name to ID if needed
        channel_id = await _resolve_channel_id(client, channel)
        payload: dict[str, Any] = {"channel": channel_id, "text": body_text[:4000]}
        if thread_ts:
            payload["thread_ts"] = thread_ts

        response = await client.post(
            f"{_BASE_URL}/chat.postMessage", headers=_headers(), json=payload
        )
        data = response.json()
        
        # Auto-join if needed
        if not data.get("ok") and data.get("error") == "not_in_channel":
            logger.info("slack_autojoin_attempt", channel=channel_id)
            join_resp = await client.post(
                f"{_BASE_URL}/conversations.join", headers=_headers(), json={"channel": channel_id}
            )
            join_data = join_resp.json()
            if not join_data.get("ok"):
                err = join_data.get("error", "unknown")
                if err == "missing_scope":
                    raise RuntimeError(
                        "Slack API error: Bot lacks 'channels:join' scope. "
                        "Please add it in the Slack App Dashboard or manually invite the bot to the channel."
                    )
                raise RuntimeError(f"Slack API error: Bot failed to auto-join channel ({err}). Invite the bot manually.")
                
            # Final retry
            response = await client.post(
                f"{_BASE_URL}/chat.postMessage", headers=_headers(), json=payload
            )
            data = response.json()

        if not data.get("ok"):
            raise RuntimeError(f"Slack API error: {data.get('error')}")
            
        return {"ok": True, "ts": data.get("ts"), "channel": data.get("channel")}


async def slack_archive_channel(*, channel: str) -> dict[str, Any]:
    """Archive a Slack channel (HITL-gated write operation) with auto-join.

    Args:
        channel: Channel ID or name (e.g. #general).

    Returns:
        Slack response.
    """
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        channel_id = await _resolve_channel_id(client, channel)
        payload = {"channel": channel_id}
        
        response = await client.post(
            f"{_BASE_URL}/conversations.archive", headers=_headers(), json=payload
        )
        data = response.json()
        
        # Auto-join if needed
        if not data.get("ok") and data.get("error") == "not_in_channel":
            logger.info("slack_autojoin_archive_attempt", channel=channel_id)
            join_resp = await client.post(
                f"{_BASE_URL}/conversations.join", headers=_headers(), json={"channel": channel_id}
            )
            join_data = join_resp.json()
            if not join_data.get("ok"):
                raise RuntimeError(f"Slack API error: Bot failed to auto-join channel to archive ({join_data.get('error')}).")
                
            # Retry archive
            response = await client.post(
                f"{_BASE_URL}/conversations.archive", headers=_headers(), json=payload
            )
            data = response.json()

        if not data.get("ok"):
            raise RuntimeError(f"Slack API error: {data.get('error')}")
            
        return {"ok": True, "channel": channel_id}


async def slack_list_channels(*, limit: int = 20) -> dict[str, Any]:
    """List public Slack channels."""
    params = {"limit": limit, "exclude_archived": "true"}
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.get(
            f"{_BASE_URL}/conversations.list",
            headers=_headers(),
            params=params,
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        if not data.get("ok"):
            raise RuntimeError(f"Slack API error: {data.get('error')}")
        channels = [
            {"id": c["id"], "name": c["name"], "num_members": c.get("num_members")}
            for c in data.get("channels", [])
        ]
        return {"channels": channels}


async def slack_check_health() -> dict[str, Any]:
    """Check Slack API connectivity using auth.test.

    Returns:
        Health status dict.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{_BASE_URL}/auth.test", headers=_headers()
            )
            response.raise_for_status()
            data = response.json()
            
            # Extract scopes from headers if available
            scopes = response.headers.get("X-OAuth-Scopes", "unknown")
            
            if data.get("ok"):
                return {
                    "status": "connected", 
                    "team": data.get("team"), 
                    "user": data.get("user"),
                    "scopes": [s.strip() for s in scopes.split(",")] if scopes != "unknown" else []
                }
            return {"status": "error", "error": data.get("error"), "scopes": scopes}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": str(exc)}
