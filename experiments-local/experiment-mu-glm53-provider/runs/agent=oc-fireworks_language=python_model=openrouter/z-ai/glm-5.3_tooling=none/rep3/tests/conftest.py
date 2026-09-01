"""Shared fixtures: the loaded dataset (once per session) and MCP servers."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from brsoccer.data import SoccerData

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def sd() -> SoccerData:
    """The full dataset, loaded once for the whole test session."""
    return SoccerData.load(REPO_ROOT / "data" / "kaggle")


@pytest.fixture(scope="session")
def server(sd):
    """An in-process MCPServer with the datasets pre-loaded."""
    from brsoccer.mcp_server import build_server

    return build_server(sd)


def call_tool(server, name: str, args: dict) -> str:
    """Invoke an MCP tool synchronously and return its text output."""

    async def _call() -> str:
        result = await server.call_tool(name, args)
        assert result.is_error is False, f"tool {name} failed"
        return result.content[0].text if result.content else ""

    return asyncio.run(_call())
