"""
Pytest configuration and shared fixtures for Brazilian Soccer MCP tests.

The data store is loaded once per test session because the six CSV files
are large and slow to normalize.
"""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp.data_store import DataStore


@pytest.fixture(scope="session")
def data_store() -> DataStore:
    """Return a fully-loaded DataStore shared across all tests."""
    return DataStore()
