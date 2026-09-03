"""Shared pytest fixtures for the Brazilian Soccer MCP test suite.

The fixtures load the bundled Kaggle datasets once per session (the loader is
cached) so the whole suite stays well within the spec's performance budget
(simple lookups < 2s, aggregate queries < 5s).
"""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp.data_loader import SoccerData, load_all
from brazilian_soccer_mcp.server import get_server


@pytest.fixture(scope="session")
def data() -> SoccerData:
    return load_all()


@pytest.fixture(scope="session")
def server():
    return get_server()
