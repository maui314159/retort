"""BDD tests for the MCP server tool surface (server.py).

Context block
-------------
Feature: MCP Tools
  The server module is a thin adapter over analysis.* — these tests
  verify every tool is registered, returns valid JSON, and delegates
  correctly. Server imports must not crash.
"""
from __future__ import annotations

import json

import server


class TestServerTools:
    # Scenario: Server exposes all required tools
    def test_all_tools_registered(self):
        tools = server.mcp._tool_manager.list_tools()
        # _tool_manager.list_tools returns Tool objects in mcp v1
        names = {t.name for t in tools}
        required = {
            "search_matches_tool", "head_to_head_tool", "team_stats_tool",
            "standings_tool", "champion_tool", "relegated_teams_tool",
            "biggest_wins_tool", "average_goals_tool", "best_home_record_tool",
            "derbies_tool", "search_players_tool", "top_brazilian_players_tool",
            "players_at_club_tool",
        }
        assert required.issubset(names), f"missing: {required - names}"

    # Scenario: Tool functions return valid JSON strings
    def test_team_stats_tool_returns_json(self):
        out = server.team_stats_tool("Flamengo", 2022)
        data = json.loads(out)
        assert data["team"] == "Flamengo"
        assert data["season"] == 2022
        assert "wins" in data

    def test_champion_tool_returns_json(self):
        out = server.champion_tool("Brasileirão", 2019)
        data = json.loads(out)
        assert data["champion"] == "Flamengo"

    def test_top_brazilian_players_tool(self):
        out = server.top_brazilian_players_tool(3)
        data = json.loads(out)
        assert len(data) == 3

    def test_average_goals_tool(self):
        out = server.average_goals_tool("Brasileirão")
        data = json.loads(out)
        assert data["matches"] > 0
