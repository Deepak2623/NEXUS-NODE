"""Supabase singleton client factory."""

from __future__ import annotations

import os

import structlog
from supabase import Client, create_client

logger: structlog.BoundLogger = structlog.get_logger(__name__)

_client: Client | None = None


def get_supabase_client() -> Client:
    """Return a cached Supabase client, creating one if needed.

    Returns:
        Authenticated Supabase Client instance.

    Raises:
        RuntimeError: If required environment variables are missing.
    """
    global _client  # noqa: PLW0603
    if _client is None:
        try:
            from config import get_settings
            settings = get_settings()
            url = settings.supabase_url
            key = settings.supabase_service_key.get_secret_value()
            if not url or "placeholder" in url or "placeholder" in key:
                logger.warning("supabase_client_using_placeholders")
            _client = create_client(url, key)
        except Exception as e:
            logger.error("supabase_client_init_failed", error=str(e))
            # Return a proxy object or just allow it to fail at call time
            # For emergency fix, we'll let it be None and handle it in routes
            raise RuntimeError(f"Supabase init failed: {str(e)}") from e
    return _client
