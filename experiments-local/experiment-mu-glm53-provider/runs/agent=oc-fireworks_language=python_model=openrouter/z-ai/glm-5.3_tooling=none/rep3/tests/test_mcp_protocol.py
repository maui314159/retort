"""Feature: MCP Protocol Integration (end-to-end over stdio)

    Scenario: An MCP client connects to the server
      Given the server runs as a stdio subprocess (server.py)
      When the client initializes the session
      Then tools are listed and callable with real answers

    Scenario: Bad arguments produce friendly text, not crashes
      When the client calls a tool with an unknown team
      Then the tool returns helpful guidance text
"""

from __future__ import annotations

import asyncio
import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

pytestmark = pytest.mark.integration

REPO_ROOT = __file__.rsplit("/tests/", 1)[0]


def _server_params() -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=[f"{REPO_ROOT}/server.py"],
        cwd=REPO_ROOT,
    )


class TestMcpStdioProtocol:
    """Scenario: Real MCP client-server session over stdio."""

    def test_initialize_list_tools_and_call(self):
        async def scenario():
            # Given the server running over stdio
            async with stdio_client(_server_params()) as (read, write):
                async with ClientSession(read, write) as session:
                    # When the client initializes
                    init = await session.initialize()
                    # Then the server reports its identity
                    assert init.server_info.name == "brazilian-soccer"
                    # And lists all 16 tools
                    tools = await session.list_tools()
                    names = {tool.name for tool in tools.tools}
                    expected = {
                        "find_team",
                        "search_matches",
                        "head_to_head",
                        "team_stats",
                        "last_match",
                        "team_competitions",
                        "standings",
                        "relegation",
                        "competition_info",
                        "competition_stats",
                        "biggest_wins",
                        "best_records",
                        "derbies",
                        "search_players",
                        "club_overview",
                        "data_summary",
                    }
                    assert expected <= names
                    # And a standings call answers over the wire
                    result = await session.call_tool(
                        "standings", {"competition": "serie_a", "season": 2019}
                    )
                    assert not result.is_error
                    text = result.content[0].text
                    assert "1. Flamengo - 90 pts (28W, 6D, 4L) - Champion" in text
                    # And a player search works too
                    result = await session.call_tool(
                        "search_players", {"name": "Neymar"}
                    )
                    assert "Neymar Jr - Overall: 92" in result.content[0].text

        asyncio.run(scenario())

    def test_tool_schemas_declare_input_types(self):
        async def scenario():
            async with stdio_client(_server_params()) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    by_name = {t.name: t for t in tools.tools}
                    # The search_matches schema exposes its filters
                    schema = by_name["search_matches"].input_schema
                    props = schema.get("properties", {})
                    for field in (
                        "team",
                        "opponent",
                        "competition",
                        "season",
                        "date_from",
                        "date_to",
                        "stage",
                        "limit",
                    ):
                        assert field in props, f"search_matches missing {field}"
                    # And required fields are enforced where needed
                    assert "name" in by_name["find_team"].input_schema.get("required", [])

        asyncio.run(scenario())

    def test_unknown_team_returns_friendly_guidance(self):
        async def scenario():
            async with stdio_client(_server_params()) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    # When the client asks for a nonexistent team
                    result = await session.call_tool(
                        "team_stats", {"team": "Manchester United"}
                    )
                    # Then the tool answers with guidance text, not a crash
                    assert not result.is_error
                    text = result.content[0].text
                    assert "No team found" in text
                    # And the unknown-competition path too
                    result = await session.call_tool(
                        "standings", {"competition": "la liga"}
                    )
                    assert not result.is_error
                    assert "Unknown competition" in result.content[0].text

        asyncio.run(scenario())
