"""Conftest — shared pytest fixtures for NEXUS-NODE backend tests."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture(autouse=True)
def _mock_supabase():
    """Auto-mock Supabase so tests never hit the real DB."""
    with patch("governance.supabase_client.get_supabase_client") as mock:
        client = mock.return_value
        # audit_log is insert-only
        client.table.return_value.insert.return_value.execute.return_value.data = [{"id": "test-id"}]
        # tasks table
        client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []
        yield mock


@pytest.fixture(autouse=True)
def _mock_audit_log():
    """Auto-mock audit logging so tests don't need Supabase credentials."""
    with patch("governance.auditor.log_audit_event", new_callable=AsyncMock):
        yield
