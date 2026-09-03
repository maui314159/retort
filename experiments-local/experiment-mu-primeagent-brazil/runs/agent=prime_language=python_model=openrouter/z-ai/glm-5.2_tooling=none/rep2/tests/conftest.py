"""
Context block
=============
Brazilian Soccer MCP Server - Pytest Configuration & Shared Fixtures
---------------------------------------------------------------------
Provides a shared, cached QueryEngine fixture used by every BDD scenario and
plain test. Loading all six CSVs once keeps the suite fast.
"""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp import get_engine, reset_cache
from brazilian_soccer_mcp.queries import QueryEngine


@pytest.fixture(scope="session")
def engine() -> QueryEngine:
    """A single QueryEngine reused across the whole test session."""
    reset_cache()
    return get_engine()
