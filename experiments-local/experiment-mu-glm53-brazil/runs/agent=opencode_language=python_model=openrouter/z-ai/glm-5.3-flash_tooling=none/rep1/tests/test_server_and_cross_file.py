"""Tests for cross-file (player + match) queries and the MCP server (R1)."""

import asyncio
import json

from brazilian_soccer_mcp.queries import QueryEngine
from brazilian_soccer_mcp.server import create_server

EXPECTED_TOOLS = {
    "search_matches",
    "get_team_stats",
    "head_to_head",
    "search_players",
    "get_standings",
    "get_competition_stats",
    "get_best_records",
    "search_derbies",
    "get_team_competitions",
    "get_club_overview",
    "get_season_summary",
    "compare_seasons",
    "list_teams",
    "list_competitions",
}


class TestClubOverview:
    def test_club_with_fifa_squad(self, engine: QueryEngine):
        result = engine.get_club_overview(team="Santos")
        assert result["all_time_record"]["played"] > 500
        squad = result["fifa_squad"]
        assert squad["player_count"] > 0
        assert squad["avg_overall"] is not None
        assert squad["top_players"]
        overalls = [p["overall"] for p in squad["top_players"]]
        assert overalls == sorted(overalls, reverse=True)

    def test_overview_club_alias(self, engine: QueryEngine):
        result = engine.get_club_overview(team="Sport Recife")
        assert result["fifa_squad"]["player_count"] == 20
        assert "Sport Club do Recife" in result["fifa_squad"]["matched_clubs"]

    def test_overview_combines_match_and_player_data(self, engine: QueryEngine):
        result = engine.get_club_overview(team="Grêmio")
        assert result["all_time_record"]["goals_for"] > 0
        assert result["competitions_played"]
        assert result["fifa_squad"]["player_count"] == 20

    def test_club_without_fifa_data_still_returns_matches(self, engine: QueryEngine):
        result = engine.get_club_overview(team="Palmeiras")
        assert result["all_time_record"]["played"] > 500
        assert result["fifa_squad"]["player_count"] >= 0


class TestMCPServer:
    def test_server_creates_with_instructions(self):
        server = create_server()
        assert server.name == "brazilian-soccer"
        assert server.instructions

    def test_all_tools_registered(self):
        server = create_server()
        tools = asyncio.run(server.list_tools())
        names = {tool.name for tool in tools}
        assert EXPECTED_TOOLS <= names
        assert all(tool.description for tool in tools)

    def test_tool_call_search_matches(self):
        server = create_server()
        result = asyncio.run(
            server.call_tool(
                "search_matches",
                {"team": "Flamengo", "opponent": "Fluminense", "limit": 3},
            )
        )
        payload = json.loads(result.content[0].text)
        assert payload["total_matches"] > 0
        assert payload["matches"][0]["competition"]

    def test_tool_call_get_standings(self):
        server = create_server()
        result = asyncio.run(
            server.call_tool(
                "get_standings", {"competition": "brasileirao", "season": 2019}
            )
        )
        payload = json.loads(result.content[0].text)
        assert payload["standings"][0]["team"] == "Flamengo"

    def test_tool_call_search_players(self):
        server = create_server()
        result = asyncio.run(
            server.call_tool(
                "search_players",
                {"nationality": "Brazil", "min_overall": 90, "limit": 5},
            )
        )
        payload = json.loads(result.content[0].text)
        assert payload["total_players"] > 0
        assert all(p["overall"] >= 90 for p in payload["players"])

    def test_tool_call_get_team_stats(self):
        server = create_server()
        result = asyncio.run(
            server.call_tool(
                "get_team_stats",
                {"team": "Corinthians", "competition": "Brasileirão", "season": 2022},
            )
        )
        payload = json.loads(result.content[0].text)
        assert payload["record"]["played"] > 0

    def test_tool_call_error_surface(self):
        server = create_server()
        result = asyncio.run(
            server.call_tool(
                "search_players", {"position_category": "banana"}
            )
        )
        payload = json.loads(result.content[0].text)
        assert "error" in payload
