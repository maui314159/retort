"""
Context Block
=============

Module: tests.test_server
Purpose: Tests for the MCP server tool registration and invocation.
         Verifies that all tools are exposed and return valid JSON.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from brazilian_soccer_mcp.server import create_server


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def server():
    """Create the MCP server once per session."""
    return create_server()


def _call_tool(server, tool_name: str, args: dict | None = None) -> dict:
    """Call a tool synchronously and return the parsed JSON result."""
    args = args or {}
    result = asyncio.run(server.call_tool(tool_name, args))
    # Extract text from the first TextContent
    if result.content:
        text = result.content[0].text if hasattr(result.content[0], 'text') else str(result.content[0])
        return json.loads(text)
    return {}


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------
class TestToolRegistration:
    """Tests that all expected tools are registered."""

    def test_all_tools_registered(self, server):
        """Given the server, all 19 tools are registered."""
        tools = asyncio.run(server.list_tools())
        tool_names = {t.name for t in tools}
        expected = {
            "find_matches", "head_to_head",
            "team_statistics", "team_info", "compare_teams",
            "best_home_record", "best_away_record",
            "find_players", "top_players", "players_at_brazilian_clubs",
            "competition_standings", "competition_seasons",
            "competition_info", "all_competitions",
            "biggest_wins", "average_goals", "home_vs_away",
            "team_list", "search_all",
        }
        assert expected.issubset(tool_names), f"Missing: {expected - tool_names}"

    def test_tools_have_descriptions(self, server):
        """Given the server, each tool has a description."""
        tools = asyncio.run(server.list_tools())
        for t in tools:
            assert t.description is not None
            assert len(t.description) > 10


# ---------------------------------------------------------------------------
# Tool invocation
# ---------------------------------------------------------------------------
class TestToolInvocation:
    """Tests that tools can be called and return valid JSON."""

    def test_find_matches_tool(self, server):
        """Given the server, calling find_matches returns JSON."""
        result = _call_tool(server, "find_matches", {"team": "Flamengo", "limit": 3})
        assert "matches" in result
        assert result["count"] <= 3

    def test_head_to_head_tool(self, server):
        """Given the server, calling head_to_head returns JSON."""
        result = _call_tool(server, "head_to_head", {"team1": "Flamengo", "team2": "Fluminense"})
        assert "team1_wins" in result
        assert "total_matches" in result

    def test_team_statistics_tool(self, server):
        """Given the server, calling team_statistics returns JSON."""
        result = _call_tool(server, "team_statistics", {"team": "Palmeiras"})
        assert "wins" in result
        assert "matches" in result

    def test_find_players_tool(self, server):
        """Given the server, calling find_players returns JSON."""
        result = _call_tool(server, "find_players", {"nationality": "Brazil", "limit": 5})
        assert "players" in result
        assert result["count"] <= 5

    def test_competition_standings_tool(self, server):
        """Given the server, calling competition_standings returns JSON."""
        result = _call_tool(server, "competition_standings",
                            {"competition": "Brasileirao", "season": 2019})
        assert "standings" in result
        assert result["champion"] is not None

    def test_biggest_wins_tool(self, server):
        """Given the server, calling biggest_wins returns JSON."""
        result = _call_tool(server, "biggest_wins", {"limit": 5})
        assert "biggest_wins" in result

    def test_all_competitions_tool(self, server):
        """Given the server, calling all_competitions returns JSON."""
        result = _call_tool(server, "all_competitions")
        assert "competitions" in result
        assert len(result["competitions"]) > 0

    def test_team_list_tool(self, server):
        """Given the server, calling team_list returns JSON."""
        result = _call_tool(server, "team_list", {"limit": 10})
        assert "teams" in result

    def test_search_all_tool(self, server):
        """Given the server, calling search_all returns JSON."""
        result = _call_tool(server, "search_all", {"query": "Flamengo"})
        assert "teams" in result
        assert "players" in result
