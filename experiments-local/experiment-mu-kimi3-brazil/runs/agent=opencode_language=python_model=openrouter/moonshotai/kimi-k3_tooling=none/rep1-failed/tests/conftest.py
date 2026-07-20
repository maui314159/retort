"""Shared pytest fixtures."""

import pytest

from brazilian_soccer_mcp.data import get_dataset


@pytest.fixture(scope="session")
def ds():
    """Session-scoped Dataset (CSVs are loaded only once per test run)."""
    return get_dataset()
