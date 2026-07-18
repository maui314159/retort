"""Tests for the MCP server (R1: MCP protocol server with registered tools).

Verifies that:
  - The FastMCP server is instantiated.
  - All required query tools are registered.
  - Tools can be called through the MCP protocol and return structured data.
  - A resource is exposed for data discovery.
"""
from __future__ import annotations

import asyncio


from brazilian_soccer.server import mcp


REQUIRED_TOOLS = {
    "tool_find_matches",           # R3/R4/R5
    "tool_head_to_head",           # R11
    "tool_team_statistics",        # R6
    "tool_team_competitions",      # R6
    "tool_search_players",         # R7/R8
    "tool_top_players_at_club",    # R7/R8
    "tool_competition_standings",  # R9
    "tool_competition_champion",   # R9
    "tool_relegated_teams",        # R9
    "tool_average_goals",          # R10
    "tool_biggest_wins",           # R10
    "tool_best_team_record",       # R10
    "tool_derbies",                # R10
    "tool_data_summary",           # discovery
}


def _list_tools_sync():
    return asyncio.run(mcp.list_tools())


def _list_resources_sync():
    return asyncio.run(mcp.list_resources())


def _call_tool_sync(name, arguments):
    return asyncio.run(mcp.call_tool(name, arguments))


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

def test_server_has_required_tools():
    tools = _list_tools_sync()
    names = {t.name for t in tools}
    missing = REQUIRED_TOOLS - names
    assert not missing, f"Missing MCP tools: {missing}"


def test_server_has_resource():
    resources = _list_resources_sync()
    uris = {str(r.uri) for r in resources}
    assert "data://summary" in uris


def test_server_name():
    assert mcp.name == "brazilian-soccer-mcp"


# ---------------------------------------------------------------------------
# Tool invocations through the MCP protocol
# ---------------------------------------------------------------------------

def _extract_json(result):
    """Extract the JSON list/dict from a ToolResult's text content."""
    import json
    text = result.content[0].text
    return json.loads(text)


def test_tool_find_matches_callable():
    result = _call_tool_sync("tool_find_matches", {
        "team": "Flamengo", "season": 2023, "limit": 5,
    })
    matches = _extract_json(result)
    assert isinstance(matches, list)
    assert len(matches) > 0
    for m in matches:
        assert "home_team" in m
        assert "away_team" in m
        assert "competition" in m


def test_tool_head_to_head_callable():
    result = _call_tool_sync("tool_head_to_head", {
        "team_a": "Flamengo", "team_b": "Fluminense", "limit": 50,
    })
    h2h = _extract_json(result)
    assert h2h["matches_found"] > 0
    assert "team_a_wins" in h2h
    assert "team_b_wins" in h2h


def test_tool_team_statistics_callable():
    result = _call_tool_sync("tool_team_statistics", {
        "team": "Palmeiras", "season": 2023,
    })
    rec = _extract_json(result)
    assert rec["played"] > 0
    assert "wins" in rec and "losses" in rec and "draws" in rec


def test_tool_search_players_callable():
    result = _call_tool_sync("tool_search_players", {
        "nationality": "Brazil", "limit": 5,
    })
    players = _extract_json(result)
    assert isinstance(players, list)
    assert len(players) > 0
    for p in players:
        assert p["nationality"] == "Brazil"
        assert p["overall"] is not None


def test_tool_competition_standings_callable():
    result = _call_tool_sync("tool_competition_standings", {
        "competition": "Brasileirão Série A", "season": 2019, "top": 3,
    })
    standings = _extract_json(result)
    assert len(standings) > 0
    assert standings[0]["position"] == 1


def test_tool_average_goals_callable():
    result = _call_tool_sync("tool_average_goals", {
        "competition": "Brasileirão Série A",
    })
    stats = _extract_json(result)
    assert stats["matches"] > 0
    assert stats["avg_goals_per_match"] > 0


def test_tool_biggest_wins_callable():
    result = _call_tool_sync("tool_biggest_wins", {"limit": 3})
    wins = _extract_json(result)
    assert len(wins) > 0
    assert wins[0]["goal_difference"] > 0


def test_tool_data_summary_callable():
    result = _call_tool_sync("tool_data_summary", {})
    summary = _extract_json(result)
    assert summary["matches_total"] > 0
    assert summary["players_total"] > 0
