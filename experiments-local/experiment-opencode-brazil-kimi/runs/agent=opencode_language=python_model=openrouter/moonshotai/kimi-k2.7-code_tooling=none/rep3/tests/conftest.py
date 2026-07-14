"""
Shared fixtures for the Brazilian Soccer MCP test suite.

The engine is loaded once per session because ingesting and normalising the
bundled CSVs is the most expensive part of the test run.
"""

import pytest

from brazilian_soccer_mcp.data_loader import load_all
from brazilian_soccer_mcp.engine import SoccerEngine


@pytest.fixture(scope="session")
def engine() -> SoccerEngine:
    """Provide a single SoccerEngine instance for the whole test session."""
    data = load_all()
    return SoccerEngine(data["matches"], data["players"])


@pytest.fixture(scope="session")
def loaded_data() -> dict:
    """Provide the raw loaded data dict for low-level checks."""
    return load_all()
