"""Supabase singleton client factory."""

from __future__ import annotations

import os

from supabase import Client, create_client

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
        from config import get_settings
        settings = get_settings()
        url = settings.supabase_url
        key = settings.supabase_service_key.get_secret_value()
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables must be set."
            )
        _client = create_client(url, key)
    return _client
