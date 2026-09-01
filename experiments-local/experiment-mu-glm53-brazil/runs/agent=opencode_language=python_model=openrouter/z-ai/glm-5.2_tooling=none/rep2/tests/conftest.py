# SPDX-License-Identifier: Apache-2.0
# Test fixtures and helpers shared across the BDD test suite.
"""Shared pytest fixtures for the Brazilian soccer MCP test suite."""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp.data_loader import DataLoader
from brazilian_soccer_mcp.queries import QueryEngine


@pytest.fixture(scope="session")
def loader() -> DataLoader:
    """Load all datasets once per test session."""
    dl = DataLoader()
    dl.load_all()
    return dl


@pytest.fixture(scope="session")
def engine(loader: DataLoader) -> QueryEngine:
    """A shared QueryEngine (indexed once per session)."""
    return QueryEngine(loader)
