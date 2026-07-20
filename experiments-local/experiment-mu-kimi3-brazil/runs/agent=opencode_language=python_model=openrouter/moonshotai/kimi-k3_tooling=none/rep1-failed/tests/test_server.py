"""Tests for the FastMCP server surface: registration and tool calls."""

import asyncio
import json

import pytest

from brazilian_soccer_mcp.server import mcp

EXPECTED_TOOLS = {
    "find_matches",
    "head_to_head",
    "team_statistics",
    "team_competitions",
    "standings",
    "list_competitions",
    "list_teams",
    "biggest_wins",
    "competition_overview",
    "search_players",
    "top_players",
    "players_by_club",
    "dataset_info",
}


def _call(tool, args):
    result = asyncio.run(mcp.call_tool(tool, args))
    # FastMCP returns a ToolResult whose text content is JSON.
    text = result.content[0].text
    return json.loads(text)


def test_all_tools_registered():
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert EXPECTED_TOOLS <= names
    for t in tools:
        assert t.description, f"tool {t.name} needs a description"


def test_dataset_info_tool():
    info = _call("dataset_info", {})
    assert info["total_matches"] > 16_000
    assert info["total_players"] > 18_000
    assert len(info["matches_by_source"]) == 5


def test_find_matches_tool():
    res = _call("find_matches", {"team": "Flamengo", "opponent": "Fluminense", "limit": 5})
    assert res["count"] > 0
    assert len(res["matches"]) <= 5


def test_head_to_head_tool():
    res = _call("head_to_head", {"team_a": "Palmeiras", "team_b": "Santos"})
    assert res["matches_played"] == res["team_a_wins"] + res["team_b_wins"] + res["draws"]


def test_team_statistics_tool():
    res = _call("team_statistics", {"team": "Corinthians", "season": 2019, "venue": "home"})
    assert res["matches"] > 0
    assert 0 <= res["win_rate_pct"] <= 100


def test_standings_tool():
    res = _call("standings", {"season": 2019})
    assert res["champion"] == "Flamengo"
    assert res["table"][0]["points"] == 90


def test_player_tools():
    res = _call("search_players", {"name": "Neymar"})
    assert res["players"][0]["name"] == "Neymar Jr"
    top = _call("top_players", {"nationality": "Brazil", "limit": 3})
    assert top["players"][0]["name"] == "Neymar Jr"
    clubs = _call("players_by_club", {"nationality": "Brazil", "limit": 5})
    assert len(clubs["clubs"]) > 0


def test_stats_tools():
    wins = _call("biggest_wins", {"limit": 3})
    assert wins["results"][0]["margin"] >= wins["results"][-1]["margin"]
    overview = _call("competition_overview", {"competition": "Brasileirão Série A", "season": 2019})
    assert overview["matches"] == 380
    comps = _call("list_competitions", {})
    assert comps["count"] >= 5
    teams = _call("list_teams", {"competition": "Brasileirão Série A", "season": 2019})
    assert teams["count"] == 20
    tc = _call("team_competitions", {"team": "Flamengo"})
    assert tc["count"] >= 3


def test_tool_error_surfaces():
    with pytest.raises(Exception):
        _call("standings", {"season": 1950})
