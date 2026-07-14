"""
Context
=======
Module: tests.test_formatting_and_server
Purpose: BDD scenarios for the presentation layer and the MCP wiring — verify
         formatted text blocks match the spec's answer shape, and that the
         FastMCP server registers every capability tool and they execute
         end-to-end against the real knowledge base.
"""

from __future__ import annotations

import asyncio

from brazilian_soccer_mcp import formatting


class TestFormatting:
    """Feature: Render structured results as readable text."""

    def test_match_block_shape(self):
        rows = [{
            "date": "2019-10-20", "season": 2019, "competition": "Brasileirão Série A",
            "home_team": "Flamengo-RJ", "away_team": "Fluminense-RJ",
            "home_goal": 2, "away_goal": 1, "stage": "Round 28",
        }]
        text = formatting.format_matches(rows, "Fla-Flu:")
        assert "Fla-Flu:" in text
        assert "Flamengo-RJ 2-1 Fluminense-RJ" in text
        assert "Brasileirão Série A" in text

    def test_team_stats_block_shape(self):
        s = {
            "team": "Corinthians", "season": 2022, "competition": "Brasileirão Série A",
            "venue": "home", "matches": 19, "wins": 11, "draws": 5, "losses": 3,
            "goals_for": 28, "goals_against": 15, "goal_difference": 13,
            "points": 38, "win_rate": 57.9,
        }
        text = formatting.format_team_stats(s)
        assert "Wins: 11, Draws: 5, Losses: 3" in text
        assert "Win rate: 57.9%" in text

    def test_empty_results_are_handled(self):
        assert "No matches" in formatting.format_matches([])
        assert "No players" in formatting.format_players([])


class TestMcpServer:
    """Feature: MCP server exposes the query engine as tools."""

    def test_all_capability_tools_registered(self):
        from brazilian_soccer_mcp import server

        tools = asyncio.run(server.mcp.list_tools())
        names = {t.name for t in tools}
        expected = {
            "dataset_overview", "search_matches", "head_to_head", "team_record",
            "team_competitions", "search_players", "players_by_club",
            "league_standings", "competition_statistics", "biggest_wins",
            "top_scoring_teams",
        }
        assert expected <= names

    def test_search_matches_tool_executes(self):
        from brazilian_soccer_mcp import server

        out = asyncio.run(server.mcp.call_tool(
            "search_matches", {"team": "Flamengo", "opponent": "Fluminense"}
        ))
        # FastMCP returns (content_blocks, structured) — just assert non-empty text.
        text = str(out)
        assert "Flamengo" in text and "Fluminense" in text

    def test_standings_tool_executes(self):
        from brazilian_soccer_mcp import server

        out = asyncio.run(server.mcp.call_tool(
            "league_standings", {"competition": "Brasileirão Série A", "season": 2019}
        ))
        assert "Flamengo" in str(out)
