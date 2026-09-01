"""Shared fixtures for the Brazilian Soccer MCP BDD test suite.

The datasets are loaded once per session (loading takes about one second)
and shared by every scenario via the ``data``, ``service`` and ``server``
fixtures.
"""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp.loader import SoccerData
from brazilian_soccer_mcp.server import build_server
from brazilian_soccer_mcp.service import SoccerQueryService


@pytest.fixture(scope="session")
def data() -> SoccerData:
    return SoccerData.load()


@pytest.fixture(scope="session")
def service(data: SoccerData) -> SoccerQueryService:
    return SoccerQueryService(data)


@pytest.fixture(scope="session")
def server(data: SoccerData):
    return build_server(data)
