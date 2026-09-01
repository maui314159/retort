"""BDD scenarios for the MCP server layer.

Calls each tool through the real ``MCPServer.call_tool`` API so the
protocol wiring (schemas, serialization) is exercised end to end.
"""

from __future__ import annotations

import json

import pytest

from soccer.server import build_server


def _payload(result) -> dict:
    """Extract the JSON payload from a CallToolResult."""
    assert not result.is_error, result
    blocks = result.content
    assert blocks, "tool returned no content"
    return json.loads(blocks[0].text)


@pytest.mark.asyncio
async def test_tools_are_listed(server):
    """Given the server is built, it advertises its tools."""
    tools = await server.list_tools()
    names = {t.name for t in tools}
    assert {
        "find_matches",
        "head_to_head",
        "team_stats",
        "standings",
        "search_players",
        "goals_statistics",
    } <= names


@pytest.mark.asyncio
async def test_find_matches_tool(server):
    """Scenario: find matches between two teams via the MCP tool."""
    result = await server.call_tool(
        "find_matches",
        {"team": "Flamengo", "opponent": "Fluminense", "limit": 5},
    )
    payload = _payload(result)
    assert payload["total"] > 20
    assert len(payload["matches"]) == 5
    for m in payload["matches"]:
        assert {"date", "score", "competition"} <= set(m)


@pytest.mark.asyncio
async def test_team_stats_tool(server):
    result = await server.call_tool(
        "team_stats", {"team": "Corinthians", "season": 2022, "venue": "home"}
    )
    payload = _payload(result)
    assert payload["matches"] > 15
    assert payload["win_rate"] > 0


@pytest.mark.asyncio
async def test_standings_tool(server):
    result = await server.call_tool("standings", {"season": 2019, "limit": 5})
    payload = _payload(result)
    assert payload["standings"][0]["team"] == "Flamengo"


@pytest.mark.asyncio
async def test_search_players_tool(server):
    result = await server.call_tool(
        "search_players", {"nationality": "Brazil", "limit": 5}
    )
    payload = _payload(result)
    assert payload["players"][0]["overall"] >= 88


@pytest.mark.asyncio
async def test_goals_statistics_tool(server):
    result = await server.call_tool("goals_statistics", {"competition": "Brasileirão"})
    payload = _payload(result)
    assert 1.5 < payload["avg_goals_per_match"] < 3.5


@pytest.mark.asyncio
async def test_list_teams_and_competitions_tools(server):
    teams = _payload(await server.call_tool("list_teams", {}))
    assert "flamengo" in teams["teams"]
    comps = _payload(await server.call_tool("list_competitions", {}))
    names = {c["competition"] for c in comps["competitions"]}
    assert "Copa Libertadores" in names


@pytest.mark.asyncio
async def test_error_on_unknown_tool(server):
    from mcp.server.mcpserver.exceptions import ToolError

    with pytest.raises(ToolError):
        await server.call_tool("nonexistent_tool", {})
