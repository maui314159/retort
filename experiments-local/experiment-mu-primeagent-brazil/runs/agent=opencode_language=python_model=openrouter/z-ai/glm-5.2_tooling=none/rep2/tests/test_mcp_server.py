"""BDD tests: the MCP server surface.

Feature: MCP Server
  Scenario: List and call tools
    Given the MCP server is built
    When I list its tools
    Then all required query tools should be present
    And calling the "champion" tool returns a JSON text result

These tests run the SDK's coroutines through ``asyncio.run`` so no extra
``pytest-asyncio`` plugin is required.
"""
from __future__ import annotations

import asyncio
import json

from brsl.server import build_server

REQUIRED_TOOLS = {
    "search_matches", "head_to_head", "team_stats", "team_competitions",
    "team_summary", "search_players", "top_brazilian_players",
    "players_at_brazilian_clubs", "team_players", "standings", "champion",
    "relegated", "cup_bracket", "average_goals", "home_vs_away",
    "biggest_victories", "top_scoring_teams", "derbies",
}


def test_server_lists_all_required_tools():
    server = build_server()
    tools = asyncio.run(server.list_tools())
    names = {t.name for t in tools}
    assert REQUIRED_TOOLS <= names


def test_call_champion_tool():
    server = build_server()
    result = asyncio.run(server.call_tool(
        "champion", {"competition": "brasileirao", "season": 2019}))
    payload = json.loads(result.content[0].text)
    assert payload["champion"].startswith("Flamengo")
    assert payload["points"] == 90


def test_call_head_to_head_tool():
    server = build_server()
    result = asyncio.run(server.call_tool(
        "head_to_head", {"team_a": "Flamengo", "team_b": "Fluminense"}))
    payload = json.loads(result.content[0].text)
    assert payload["matches"] > 0


def test_call_top_brazilian_players_tool():
    server = build_server()
    result = asyncio.run(server.call_tool(
        "top_brazilian_players", {"limit": 5}))
    payload = json.loads(result.content[0].text)
    assert payload["players"][0]["name"] == "Neymar Jr"


def test_call_derbies_tool():
    server = build_server()
    result = asyncio.run(server.call_tool("derbies", {"season": 2019}))
    payload = json.loads(result.content[0].text)
    assert payload["count"] > 0
