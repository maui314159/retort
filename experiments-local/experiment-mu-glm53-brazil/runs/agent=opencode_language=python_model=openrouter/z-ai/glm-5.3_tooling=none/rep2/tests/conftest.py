"""Shared pytest fixtures for the Brazilian Soccer MCP test suite."""

from __future__ import annotations

from pathlib import Path

import pytest

from brazilian_soccer_mcp.service import SoccerDataService

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "kaggle"


@pytest.fixture(scope="session")
def service() -> SoccerDataService:
    """Load every dataset once for the whole test session."""
    return SoccerDataService(DATA_DIR)
