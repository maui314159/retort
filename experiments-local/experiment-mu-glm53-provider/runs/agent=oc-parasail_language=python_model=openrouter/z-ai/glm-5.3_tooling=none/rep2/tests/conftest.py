"""Shared fixtures for the Brazilian Soccer MCP test suite.

The engine loads all six CSV files once per test session (~1s) and every
test (BDD scenarios, GWT modules, MCP protocol tests) reuses it.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from soccer_mcp.engine import SoccerData  # noqa: E402  (path setup above must run first)


@pytest.fixture(scope="session")
def engine() -> SoccerData:
    return SoccerData()


@pytest.fixture(scope="session")
def mcp_server():
    import server as server_module

    return server_module.server


def call_tool_sync(server, name: str, arguments: dict) -> dict:
    """Call an MCP tool on the server and parse its JSON response."""

    async def _call():
        result = await server.call_tool(name, arguments)
        text = result.content[0].text
        return json.loads(text)

    return asyncio.run(_call())
