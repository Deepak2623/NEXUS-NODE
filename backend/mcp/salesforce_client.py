"""Salesforce MCP connector — wraps Salesforce REST API via httpx."""

from __future__ import annotations

import os
from typing import Any

import httpx
import structlog
from config import get_settings

logger: structlog.BoundLogger = structlog.get_logger(__name__)
_TIMEOUT = 10.0


def _base_url() -> str:
    return get_settings().salesforce_mcp_instance_url.rstrip("/")


async def _get_access_token() -> str:
    """Obtain a Salesforce OAuth2 access token using client credentials flow.

    Returns:
        Bearer access token string.

    Raises:
        RuntimeError: If token exchange fails.
    """
    settings = get_settings()
    token_url = f"{_base_url()}/services/oauth2/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": settings.salesforce_mcp_client_id.get_secret_value(),
        "client_secret": settings.salesforce_mcp_client_secret.get_secret_value(),
    }
    verify_mode = not os.getenv("BYPASS_SSL_VERIFY", "0") == "1"
    async with httpx.AsyncClient(timeout=_TIMEOUT, verify=verify_mode) as client:
        response = await client.post(token_url, data=data, follow_redirects=True)
        if response.status_code != 200:
            raise RuntimeError(f"Salesforce auth failed: {response.text}")
        return str(response.json().get("access_token", ""))


async def salesforce_query_accounts(*, soql: str) -> dict[str, Any]:
    """Execute a SOQL query against Salesforce (read-only).

    Args:
        soql: SOQL query string. Must not contain DELETE or UPDATE.

    Returns:
        Query result with records list.

    Raises:
        ValueError: If soql contains write keywords.
        RuntimeError: On API error.
    """
    upper = soql.upper()
    if any(kw in upper for kw in ("DELETE", "UPDATE", "INSERT", "UPSERT")):
        raise ValueError("salesforce_query_accounts only supports SELECT queries.")

    # Safety: Salesforce SOQL doesn't support SELECT *
    if "SELECT *" in upper: # It replaces * to generic
        soql = soql.replace("*", "Id, Name, Type, Industry")

    token = await _get_access_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = f"{_base_url()}/services/data/v59.0/query"

    verify_mode = not os.getenv("BYPASS_SSL_VERIFY", "0") == "1"
    async with httpx.AsyncClient(timeout=_TIMEOUT, verify=verify_mode) as client:
        # Pass payload properly URL encoded
        response = await client.get(url, headers=headers, params={"q": soql})
        if response.status_code != 200:
            raise RuntimeError(f"Salesforce query failed ({response.status_code}): {response.text}")
        data: dict[str, Any] = response.json()
        records = data.get("records", [])
        logger.info("salesforce_query", total_size=data.get("totalSize"), soql=soql[:100])
        return {"totalSize": data.get("totalSize"), "records": records}


async def salesforce_update_opportunity(
    *, opportunity_id: str, fields: dict[str, Any]
) -> dict[str, Any]:
    """Update a Salesforce Opportunity record (HITL-gated write).

    Args:
        opportunity_id: Salesforce Opportunity ID (18-char).
        fields: Dict of field names to new values.

    Returns:
        Update result dict.

    Raises:
        RuntimeError: On API error.
    """
    token = await _get_access_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = f"{_base_url()}/services/data/v59.0/sobjects/Opportunity/{opportunity_id}"

    verify_mode = not os.getenv("BYPASS_SSL_VERIFY", "0") == "1"
    async with httpx.AsyncClient(timeout=_TIMEOUT, verify=verify_mode) as client:
        response = await client.patch(url, headers=headers, json=fields)
        if response.status_code not in (200, 204):
            raise RuntimeError(f"Salesforce update failed ({response.status_code}): {response.text}")
        logger.info("salesforce_update_opportunity", opportunity_id=opportunity_id)
        return {"updated": True, "id": opportunity_id}


async def salesforce_describe_object(*, object_name: str) -> dict[str, Any]:
    """Get metadata (fields, types) for a Salesforce object to discover schema dynamically.

    Args:
        object_name: The name of the Salesforce object (e.g., 'Account', 'Opportunity', 'Contact').

    Returns:
        Dict containing top fields and metadata.
    """
    token = await _get_access_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = f"{_base_url()}/services/data/v59.0/sobjects/{object_name}/describe"

    verify_mode = not os.getenv("BYPASS_SSL_VERIFY", "0") == "1"
    async with httpx.AsyncClient(timeout=_TIMEOUT, verify=verify_mode) as client:
        response = await client.get(url, headers=headers)
        if response.status_code != 200:
            raise RuntimeError(f"Salesforce describe failed ({response.status_code}): {response.text}")
        
        data = response.json()
        
        # We only want to return a subset of metadata to avoid blowing up the LLM context
        fields = [
            {
                "name": f.get("name"),
                "type": f.get("type"),
                "label": f.get("label")
            }
            for f in data.get("fields", [])
        ]
        
        return {
            "name": data.get("name"),
            "label": data.get("label"),
            "fields": fields[:200]  # limit fields to prevent context overflow
        }


async def salesforce_check_health() -> dict[str, Any]:
    """Check Salesforce API connectivity.

    Returns:
        Health status dict.
    """
    try:
        token = await _get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{_base_url()}/services/data/v59.0/limits"
        verify_mode = not os.getenv("BYPASS_SSL_VERIFY", "0") == "1"
        async with httpx.AsyncClient(timeout=5.0, verify=verify_mode) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return {"status": "connected", "api_version": "v59.0"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": str(exc)}
