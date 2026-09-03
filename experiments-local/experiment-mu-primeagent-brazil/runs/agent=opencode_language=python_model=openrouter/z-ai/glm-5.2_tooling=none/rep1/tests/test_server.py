"""BDD tests for the MCP server surface.

Feature: MCP Server

  Scenario: Tools are registered
    Given the MCP server is constructed
    When I list its tools
    Then I should see a tool for each required capability

  Scenario: Calling a tool returns valid JSON
    Given the MCP server is constructed
    When I call the "standings" tool with season 2019
    Then the response should be valid JSON with a champion
"""

from __future__ import annotations

import json

REQUIRED_TOOLS = {
    "find_matches", "head_to_head", "team_stats", "compare_teams",
    "competitions_for_team", "search_players", "top_brazilian_players",
    "players_for_club", "top_clubs_by_nationality", "standings", "champions",
    "relegated_teams", "average_goals", "biggest_wins", "home_away_balance",
    "derbies",
}


def test_tools_registered(server):
    import asyncio

    async def _run():
        tools = await server.list_tools()
        return {t.name for t in tools}

    names = asyncio.run(_run())
    missing = REQUIRED_TOOLS - names
    assert not missing, f"missing tools: {missing}"


def test_call_standings_tool(server):
    import asyncio

    async def _run():
        res = await server.call_tool("standings", {"competition": "Brasileirão Serie A",
                                                   "season": 2019})
        return res

    res = asyncio.run(_run())
    assert res.content
    payload = json.loads(res.content[0].text)
    assert payload["standings"][0]["team"] == "Flamengo"
    assert payload["standings"][0]["points"] == 90


def test_call_head_to_head_tool(server):
    import asyncio

    async def _run():
        return await server.call_tool("head_to_head",
                                      {"team_a": "Flamengo", "team_b": "Fluminense"})

    res = asyncio.run(_run())
    payload = json.loads(res.content[0].text)
    assert payload["team_a"] == "Flamengo"
    assert payload["team_b"] == "Fluminense"
    assert payload["matches_played"] > 0


def test_call_find_matches_tool(server):
    import asyncio

    async def _run():
        return await server.call_tool("find_matches",
                                      {"team": "Palmeiras", "season": 2022, "limit": 5})

    res = asyncio.run(_run())
    payload = json.loads(res.content[0].text)
    assert len(payload) <= 5
    for r in payload:
        assert r["competition"]


def test_call_top_brazilian_players_tool(server):
    import asyncio

    async def _run():
        return await server.call_tool("top_brazilian_players", {"limit": 5})

    res = asyncio.run(_run())
    payload = json.loads(res.content[0].text)
    assert payload[0]["name"] == "Neymar Jr"
