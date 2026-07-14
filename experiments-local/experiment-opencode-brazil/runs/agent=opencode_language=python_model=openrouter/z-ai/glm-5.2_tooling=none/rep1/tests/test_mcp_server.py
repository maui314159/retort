import asyncio
import json

import pytest


def _call(server, tool, args):
    return asyncio.run(server.call_tool(tool, args))


def test_server_lists_all_tools(server):
    """Feature: MCP Server
    Scenario: the server exposes the required tools
      Given the MCP server is built
      When I list the tools
      Then all five query categories are represented
    """
    tools = asyncio.run(server.list_tools())
    names = {t.name for t in tools}
    expected = {
        "search_matches", "head_to_head", "team_statistics",
        "search_player", "top_players", "players_at_club",
        "competition_standings", "competition_champion", "relegated_teams",
        "average_goals_per_match", "home_vs_away_performance", "biggest_wins",
        "derbies", "data_coverage",
    }
    assert expected.issubset(names)


def test_server_champion_tool(server):
    """Scenario: champion tool returns JSON
      When I call competition_champion
      Then the result is valid JSON naming Flamengo
    """
    content, _ = _call(server, "competition_champion",
                       {"competition": "Brasileirao", "season": 2019})
    data = json.loads(content[0].text)
    assert data["team_id"] == "flamengo"
    assert data["points"] == 90


def test_server_search_matches_tool(server):
    """Scenario: search_matches tool
      When I call search_matches for Fla-Flu
      Then I get a JSON list of matches
    """
    content, _ = _call(server, "search_matches",
                       {"team": "Flamengo", "vs_team": "Fluminense", "limit": 5})
    data = json.loads(content[0].text)
    assert isinstance(data, list)
    assert len(data) <= 5
    assert len(data) > 0


def test_server_top_players_tool(server):
    """Scenario: top_players tool
      When I call top_players for Brazil
      Then Neymar Jr is first
    """
    content, _ = _call(server, "top_players",
                       {"nationality": "Brazil", "limit": 3})
    data = json.loads(content[0].text)
    assert data[0]["name"] == "Neymar Jr"
    assert data[0]["overall"] == 92


def test_server_data_coverage_tool(server):
    """Scenario: data_coverage tool
      When I call data_coverage
      Then I get matches, players and competitions
    """
    content, _ = _call(server, "data_coverage", {})
    data = json.loads(content[0].text)
    assert data["matches_unique"] > 0
    assert data["players"] > 18000
    assert "Brasileirao" in data["competitions"]
