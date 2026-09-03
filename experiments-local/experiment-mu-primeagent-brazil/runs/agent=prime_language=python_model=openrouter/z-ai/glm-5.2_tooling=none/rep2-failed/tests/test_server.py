"""
Context block
=============
Brazilian Soccer MCP Server - MCP Server Integration Tests
----------------------------------------------------------
Verifies that the MCPServer registers all expected tools and that every tool
returns valid, JSON-decodable data. These exercise the same wrappers an LLM
client would call over the MCP protocol.
"""

from __future__ import annotations

import json

import pytest

from brazilian_soccer_mcp import create_server, list_tool_names
from brazilian_soccer_mcp import server as server_module


@pytest.fixture(scope="module")
def server():
    return create_server()


def test_server_has_all_tools(server):
    names = list_tool_names()
    expected = {
        "find_matches", "head_to_head", "last_match_between",
        "team_statistics", "team_competitions", "search_players",
        "top_brazilian_players", "players_at_club",
        "brazilian_players_by_club", "standings", "biggest_wins",
        "average_goals", "best_home_record", "best_away_record",
        "derbies", "seasons_summary",
    }
    assert expected <= set(names)
    assert len(names) == len(expected)


def test_every_tool_returns_valid_json():
    calls = {
        "find_matches": {},
        "head_to_head": {"team_a": "Flamengo", "team_b": "Fluminense"},
        "last_match_between": {"team_a": "Flamengo", "team_b": "Corinthians"},
        "team_statistics": {"team": "Palmeiras", "season": 2019},
        "team_competitions": {"team": "Palmeiras"},
        "search_players": {"nationality": "Brazil", "limit": 5},
        "top_brazilian_players": {"limit": 5},
        "players_at_club": {"club": "Grêmio"},
        "brazilian_players_by_club": {},
        "standings": {"competition": "brasileirao", "season": 2019, "top": 5},
        "biggest_wins": {"competition": "brasileirao", "limit": 5},
        "average_goals": {"competition": "brasileirao", "season": 2019},
        "best_home_record": {"competition": "brasileirao", "season": 2019, "top": 5},
        "best_away_record": {"competition": "brasileirao", "season": 2019, "top": 5},
        "derbies": {"season": 2023, "limit": 5},
        "seasons_summary": {"competition": "brasileirao"},
    }
    for name, kwargs in calls.items():
        fn = getattr(server_module, f"tool_{name}")
        result = fn(**kwargs)
        assert isinstance(result, str)
        decoded = json.loads(result)
        assert decoded is not None


def test_standings_tool_champion():
    out = json.loads(server_module.tool_standings(competition="brasileirao",
                                                  season=2019, top=1))
    assert out[0]["team"] == "Flamengo"
    assert out[0]["points"] == 90


def test_server_metadata():
    srv = create_server()
    assert srv.name == "brazilian-soccer-mcp"
    assert srv.title == "Brazilian Soccer MCP Server"


def test_mcp_server_lists_and_calls_tools():
    """Exercise the real MCPServer tool registry (async) via asyncio.run."""
    import asyncio
    srv = create_server()

    async def run():
        tools = await srv.list_tools()
        names = {t.name for t in tools}
        expected = {
            "find_matches", "head_to_head", "last_match_between",
            "team_statistics", "team_competitions", "search_players",
            "top_brazilian_players", "players_at_club",
            "brazilian_players_by_club", "standings", "biggest_wins",
            "average_goals", "best_home_record", "best_away_record",
            "derbies", "seasons_summary",
        }
        assert expected <= names
        result = await srv.call_tool(
            "standings",
            {"competition": "brasileirao", "season": 2019, "top": 1},
        )
        text = "".join(c.text for c in result.content if hasattr(c, "text"))
        data = json.loads(text)
        assert data[0]["team"] == "Flamengo"
        assert data[0]["points"] == 90

    asyncio.run(run())


def test_mcp_stdio_end_to_end():
    """Spawn the real MCP stdio server and drive it with the MCP client.

    This validates the full LLM-integration transport: initialize, list_tools
    and call_tool over stdio.
    """
    import asyncio
    import os
    import sys
    from mcp.client.stdio import stdio_client, StdioServerParameters
    from mcp.client.session import ClientSession

    async def run():
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "brazilian_soccer_mcp"],
            env={**os.environ},
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                names = {t.name for t in tools.tools}
                assert {"find_matches", "standings", "head_to_head"} <= names
                result = await session.call_tool(
                    "standings",
                    {"competition": "brasileirao", "season": 2019, "top": 1},
                )
                assert result.is_error is False
                data = json.loads(result.content[0].text)
                assert data[0]["team"] == "Flamengo"
                assert data[0]["points"] == 90

    asyncio.run(run())
