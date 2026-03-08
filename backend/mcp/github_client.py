"""GitHub MCP connector — wraps GitHub REST API via httpx."""

from __future__ import annotations

import base64
from typing import Any

import httpx
import structlog
from config import get_settings

logger: structlog.BoundLogger = structlog.get_logger(__name__)

_BASE_URL = "https://api.github.com"
_TIMEOUT = 10.0


def _headers() -> dict[str, str]:
    settings = get_settings()
    token = settings.github_mcp_token.get_secret_value()
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def github_get_repo(*, owner: str, repo: str) -> dict[str, Any]:
    """Fetch GitHub repository metadata (read-only).

    Args:
        owner: Repository owner login.
        repo: Repository name.

    Returns:
        Repository metadata dict.

    Raises:
        httpx.HTTPStatusError: On non-2xx responses.
    """
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.get(
            f"{_BASE_URL}/repos/{owner}/{repo}", headers=_headers()
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        logger.info("github_get_repo", owner=owner, repo=repo)
        return {
            "full_name": data.get("full_name"),
            "description": data.get("description"),
            "default_branch": data.get("default_branch"),
            "open_issues": data.get("open_issues_count"),
            "stars": data.get("stargazers_count"),
            "url": data.get("html_url"),
        }


async def github_create_pr(
    *,
    owner: str,
    repo: str,
    title: str,
    body: str,
    head: str,
    base: str = "main",
) -> dict[str, Any]:
    """Create a GitHub Pull Request (HITL-gated write operation).

    Args:
        owner: Repository owner login.
        repo: Repository name.
        title: PR title.
        body: PR description body.
        head: Source branch name.
        base: Target branch name (default: main).

    Returns:
        Created PR metadata.

    Raises:
        httpx.HTTPStatusError: On non-2xx responses.
    """
    payload = {"title": title, "body": body, "head": head, "base": base}
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.post(
            f"{_BASE_URL}/repos/{owner}/{repo}/pulls",
            headers=_headers(),
            json=payload,
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        logger.info("github_create_pr", owner=owner, repo=repo, pr_number=data.get("number"))
        return {
            "number": data.get("number"),
            "url": data.get("html_url"),
            "state": data.get("state"),
        }


async def github_get_file_content(
    *,
    owner: str,
    repo: str,
    path: str,
) -> dict[str, Any]:
    """Fetch file contents from a GitHub repository.

    Args:
        owner: Repository owner login.
        repo: Repository name.
        path: Path to the file.

    Returns:
        File contents.

    Raises:
        httpx.HTTPStatusError: On non-2xx responses.
    """
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.get(
            f"{_BASE_URL}/repos/{owner}/{repo}/contents/{path}",
            headers=_headers(),
            follow_redirects=True,
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        logger.info("github_get_file_content", owner=owner, repo=repo, path=path)
        
        content = data.get("content", "")
        if content and data.get("encoding") == "base64":
            try:
                content = base64.b64decode(content).decode("utf-8")
            except Exception:
                pass
                
        return {
            "name": data.get("name"),
            "path": data.get("path"),
            "content": content,
        }

async def github_check_health() -> dict[str, Any]:
    """Check GitHub API connectivity.

    Returns:
        Health status dict.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{_BASE_URL}/rate_limit", headers=_headers())
            response.raise_for_status()
            rate = response.json().get("rate", {})
            return {"status": "connected", "remaining": rate.get("remaining"), "limit": rate.get("limit")}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": str(exc)}
