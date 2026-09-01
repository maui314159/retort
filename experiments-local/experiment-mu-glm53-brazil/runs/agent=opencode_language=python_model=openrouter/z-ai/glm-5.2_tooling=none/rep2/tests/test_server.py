# SPDX-License-Identifier: Apache-2.0
# Context block ----------------------------------------------------------------
# BDD tests for the MCP server itself: verifies the server starts over stdio,
# advertises the expected tools, and that a representative tool call returns
# the documented payload shape.
#
# Uses asyncio.run() inside sync test functions so we don't need
# pytest-asyncio as an extra dependency.
# --------------------------------------------------------------------------- #
"""BDD scenarios for the MCP server surface."""

from __future__ import annotations

import asyncio
import json
import os

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


def _server_params() -> StdioServerParameters:
    # Spawn the server using the same interpreter the test suite runs on,
    # inheriting the (already-installed) venv's environment.
    env = dict(os.environ)
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)
    return StdioServerParameters(
        command="python", args=["-m", "brazilian_soccer_mcp.server"], env=env,
    )


def test_server_lists_all_tools():
    # Given a running brazilian-soccer-mcp server over stdio
    # When the client asks for the tool list
    # Then it advertises the 16 documented tools
    async def scenario():
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                return {t.name for t in tools.tools}
    names = asyncio.run(scenario())
    expected = {
        "search_matches", "head_to_head", "team_statistics",
        "competitions_for_team", "search_players",
        "top_rated_by_nationality", "top_rated_by_club",
        "list_competitions", "standings", "average_goals",
        "biggest_wins", "best_record_by_venue",
        "top_scorers_by_team", "derbies_in_season",
        "list_teams", "list_sources",
    }
    assert expected.issubset(names), expected - names


def test_server_average_goals_returns_payload():
    # Given the running server
    # When I call the average_goals tool with competition=brasileirao
    # Then I get a JSON payload with average_goals_per_match and total_matches
    async def scenario():
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                res = await session.call_tool("average_goals",
                                               {"competition": "brasileirao"})
                return json.loads(res.content[0].text)
    payload = asyncio.run(scenario())
    assert "average_goals_per_match" in payload
    assert "total_matches" in payload
    assert payload["total_matches"] > 0


def test_server_standings_2019_champion():
    # Given the running server
    # When I call standings for season 2019
    # Then the first row is the champion Flamengo
    async def scenario():
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                res = await session.call_tool("standings", {"season": 2019})
                return json.loads(res.content[0].text)
    data = asyncio.run(scenario())
    assert data
    assert data[0].get("champion") is True
    assert data[0]["team_key"] == "flamengo"


def test_server_head_to_head_tool():
    # Given the running server
    # When I call head_to_head for Fla-Flu
    # Then I get the symmetric win/draw totals
    async def scenario():
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                res = await session.call_tool("head_to_head",
                                              {"team_a": "Flamengo",
                                               "team_b": "Fluminense"})
                return json.loads(res.content[0].text)
    h2h = asyncio.run(scenario())
    assert h2h["team_a_key"] == "flamengo"
    assert h2h["team_b_key"] == "fluminense"
    assert h2h["is_derby"] is True
    total = h2h["team_a_wins"] + h2h["team_b_wins"] + h2h["draws"]
    assert total == h2h["matches_total"] > 0


def test_server_search_players_tool():
    # Given the running server
    # When I call search_players for Brazilian STs
    # Then every returned player is Brazilian and a striker
    async def scenario():
        async with stdio_client(_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                res = await session.call_tool("search_players",
                                              {"nationality": "Brazil",
                                               "position": "ST", "limit": 20})
                return json.loads(res.content[0].text)
    players = asyncio.run(scenario())
    assert players
    for p in players:
        assert p["nationality"] == "Brazil"
        assert p["position"] == "ST"
