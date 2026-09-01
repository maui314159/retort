"""BDD scenarios for the MCP server itself.

Feature: MCP server
  Scenario: The server exposes its tools over the MCP protocol
    Given the server runs on stdio
    When a client connects and lists tools
    Then all documented tools are available
    And calling a tool returns a formatted answer
"""

from __future__ import annotations

import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = os.path.join(os.path.dirname(__file__), "..", "server.py")

EXPECTED_TOOLS = {
    "search_matches",
    "head_to_head",
    "team_stats",
    "team_profile",
    "league_standings",
    "finals",
    "biggest_wins",
    "competition_info",
    "search_players",
    "players_by_club",
    "derby_matches",
}


async def _with_session(callback):
    """Connect to the server over stdio and run ``callback(session)``."""
    params = StdioServerParameters(
        command=sys.executable,
        args=[SERVER],
        cwd=os.path.dirname(SERVER),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await callback(session)


def _text(result) -> str:
    assert not result.is_error, result
    return "\n".join(
        content.text for content in result.content if hasattr(content, "text")
    )


class TestServerTools:
    def test_all_tools_are_listed(self):
        # Given the server is launched over stdio
        # When the client lists tools
        async def scenario(session):
            tools = await session.list_tools()
            return {tool.name for tool in tools.tools}

        names = asyncio.run(_with_session(scenario))
        # Then every documented tool is exposed
        assert EXPECTED_TOOLS <= names, f"missing: {EXPECTED_TOOLS - names}"

    def test_search_matches_tool_answers(self):
        # Given a connected client
        # When the search_matches tool is called
        async def scenario(session):
            return await session.call_tool(
                "search_matches",
                {"team": "Flamengo", "opponent": "Fluminense", "limit": 3},
            )

        result = asyncio.run(_with_session(scenario))
        # Then a formatted answer with matches comes back
        text = _text(result)
        assert "found" in text
        assert "Head-to-head in dataset" in text

    def test_league_standings_tool_answers(self):
        # Given a connected client
        # When the league_standings tool is called for 2019
        async def scenario(session):
            return await session.call_tool(
                "league_standings",
                {"competition": "Brasileirão", "season": 2019},
            )

        result = asyncio.run(_with_session(scenario))
        # Then the computed table names the champion
        text = _text(result)
        assert "Flamengo" in text
        assert "Champion" in text
