"""Shared fixtures for the BDD test suite.

The engine loads all six CSV datasets once per test session (about one
second), mirroring the single-load behaviour of the MCP server.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from brazilian_soccer_mcp.loader import load_data
from brazilian_soccer_mcp.queries import QueryEngine

DATA_DIR = REPO_ROOT / "data" / "kaggle"


@pytest.fixture(scope="session")
def data_dir() -> Path:
    return DATA_DIR


@pytest.fixture(scope="session")
def engine(data_dir) -> QueryEngine:
    """The query engine over all six datasets (loaded once)."""
    return QueryEngine(load_data(data_dir))


@pytest.fixture(scope="session")
def registry(engine):
    return engine.registry
