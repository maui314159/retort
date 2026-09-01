"""
Shared fixtures for the BDD test suite.

Context (Why): TASK.md's "Testing Approach" asks for BDD scenarios driven
against the real datasets ("Given the match data is loaded ..."). Loading
all six CSVs takes ~1 s, so every test module shares one session-scoped
service instance; the MCP integration tests share one in-memory server +
client session pair.

What:
    * ``service``   -- SoccerService over the real data/kaggle CSVs
    * ``data``      -- the raw SoccerData bundle (loader-level assertions)
    * ``mcp_server``-- MCPServer built around the shared service
    * ``mcp_session``-- connected ClientSession for call_tool assertions
    * ``anyio_backend`` -- asyncio for the async MCP fixtures

Test: this file is fixtures-only; see tests/test_*.py for the scenarios.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from brazilian_soccer_mcp.loaders import load_all
from brazilian_soccer_mcp.service import SoccerService
from brazilian_soccer_mcp.server import build_server

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"


@pytest.fixture(scope="session")
def data():
    """All six datasets loaded once for the whole test session."""
    return load_all(DATA_DIR)


@pytest.fixture(scope="session")
def service(data):
    """The query service, built on the shared loaded data."""
    return SoccerService(data)


@pytest.fixture(scope="session")
def mcp_server(service):
    """The MCP server wired to the shared service (no subprocess needed)."""
    return build_server(service)


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
