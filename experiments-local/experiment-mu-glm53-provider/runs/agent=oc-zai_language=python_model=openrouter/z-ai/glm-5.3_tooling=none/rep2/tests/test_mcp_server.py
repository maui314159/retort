"""Feature: MCP Server Tools

Background:
    Given the MCP server is created from the loaded dataset
    When a client lists or calls tools
    Then the protocol layer should expose and execute them correctly
"""

from __future__ import annotations

import asyncio

import pytest

from brazilian_soccer.data import load_dataset
from brazilian_soccer.server import create_server

EXPECTED_TOOLS = {
    "search_matches", "last_match_between", "head_to_head", "team_stats",
    "best_records", "team_competitions", "team_profile", "search_players",
    "top_players", "players_by_club", "standings", "champion", "bracket",
    "competition_overview", "average_goals", "biggest_wins", "derbies",
    "season_comparison",
}


def call_tool(server, name: str, arguments: dict) -> str:
    result = asyncio.run(server.call_tool(name, arguments))
    assert not result.is_error, result.content
    return result.content[0].text


@pytest.fixture(scope="module")
def server(dataset):
    return create_server(dataset)


class TestToolListing:
    """Scenario: List available tools
        Given the MCP server is running
        When I list the tools
        Then all query-capability tools should be exposed with descriptions
    """

    def test_given_running_server_when_listing_tools_then_all_expected_tools_present(self, server):
        tools = asyncio.run(server.list_tools())
        names = {tool.name for tool in tools}
        assert EXPECTED_TOOLS <= names
        for tool in tools:
            assert tool.description, tool.name

    def test_given_running_server_when_inspecting_then_server_metadata_set(self, server):
        assert server.name == "brazilian-soccer"
        assert server.instructions


class TestMatchToolCalls:
    """Scenario: Call match query tools over MCP
        Given the MCP server is running
        When I call search_matches and head_to_head
        Then I should receive formatted text answers
    """

    def test_given_flamengo_vs_fluminense_when_calling_search_matches_then_formatted_list(self, server):
        text = call_tool(server, "search_matches", {
            "team": "Flamengo", "opponent": "Fluminense", "limit": 5,
        })
        assert "Flamengo" in text and "Fluminense" in text
        assert "Fla-Flu" in text
        assert "more matches in dataset" in text

    def test_given_palmeiras_2023_when_calling_search_matches_then_season_matches(self, server):
        text = call_tool(server, "search_matches", {"team": "Palmeiras", "season": 2023})
        assert "Brasileirão Série A" in text
        assert "2023" in text

    def test_given_copa_finals_when_calling_search_matches_then_finals_listed(self, server):
        text = call_tool(server, "search_matches", {
            "competition": "Copa do Brasil", "stage": "final", "limit": 10,
        })
        assert "Final" in text


class TestTeamToolCalls:
    """Scenario: Call team query tools over MCP
        Given the MCP server is running
        When I call team_stats
        Then I should receive a record block like the specification examples
    """

    def test_given_corinthians_home_2022_when_calling_team_stats_then_record_block(self, server):
        text = call_tool(server, "team_stats", {
            "team": "Corinthians", "competition": "Serie A",
            "season": 2022, "venue": "home",
        })
        assert "Corinthians home record" in text
        assert "Matches: 19" in text
        assert "Wins: 12" in text
        assert "Win rate" in text

    def test_given_best_home_records_when_calling_best_records_then_ranked_list(self, server):
        text = call_tool(server, "best_records", {
            "competition": "Serie A", "season": 2019, "venue": "home", "min_matches": 15,
        })
        assert "Best home records" in text
        assert "1." in text


class TestPlayerToolCalls:
    """Scenario: Call player query tools over MCP
        Given the MCP server is running
        When I call search_players and top_players
        Then I should receive player listings
    """

    def test_given_neymar_when_calling_search_players_then_player_found(self, server):
        text = call_tool(server, "search_players", {"name": "Neymar"})
        assert "Neymar Jr" in text
        assert "Overall: 92" in text

    def test_given_top_brazilians_when_calling_top_players_then_neymar_first(self, server):
        text = call_tool(server, "top_players", {"nationality": "Brazil", "limit": 5})
        assert "1. Neymar Jr" in text

    def test_given_flamengo_players_when_calling_search_players_then_graceful_empty(self, server):
        text = call_tool(server, "search_players", {"club": "Flamengo"})
        assert "no players found" in text


class TestCompetitionToolCalls:
    """Scenario: Call competition query tools over MCP
        Given the MCP server is running
        When I call standings, champion and bracket
        Then I should receive formatted competition answers
    """

    def test_given_2019_serie_a_when_calling_standings_then_flamengo_champion(self, server):
        text = call_tool(server, "standings", {"competition": "Serie A", "season": 2019})
        assert "1. Flamengo - 90 pts" in text
        assert "Champion" in text

    def test_given_2019_serie_a_when_calling_standings_then_relegation_marked(self, server):
        text = call_tool(server, "standings", {"competition": "Serie A", "season": 2020})
        assert "Relegated" in text
        assert "Coritiba" in text

    def test_given_libertadores_2019_when_calling_champion_then_flamengo(self, server):
        text = call_tool(server, "champion", {"competition": "Libertadores", "season": 2019})
        assert "champion: Flamengo" in text
        assert "2-1" in text

    def test_given_2018_libertadores_when_calling_bracket_then_rounds_listed(self, server):
        text = call_tool(server, "bracket", {"competition": "Libertadores", "season": 2018})
        assert "Round of 16" in text
        assert "Quarterfinals" in text
        assert "Semifinals" in text
        assert "Final" in text
        assert "River Plate" in text

    def test_given_cup_when_calling_standings_then_helpful_error(self, server):
        text = call_tool(server, "standings", {"competition": "Libertadores", "season": 2019})
        assert "knockout" in text


class TestStatisticsToolCalls:
    """Scenario: Call statistics tools over MCP
        Given the MCP server is running
        When I call average_goals and biggest_wins
        Then I should receive aggregated statistics
    """

    def test_given_serie_a_when_calling_average_goals_then_rates_returned(self, server):
        text = call_tool(server, "average_goals", {"competition": "Serie A"})
        assert "Average goals per match" in text
        assert "Home win rate" in text

    def test_given_all_data_when_calling_biggest_wins_then_margin_listed(self, server):
        text = call_tool(server, "biggest_wins", {"limit": 3})
        assert "margin" in text

    def test_given_2023_when_calling_derbies_then_derby_matches_listed(self, server):
        text = call_tool(server, "derbies", {"season": 2023, "limit": 10})
        assert "Fla-Flu" in text or "Gre-Nal" in text

    def test_given_2018_2019_when_calling_season_comparison_then_both_seasons(self, server):
        text = call_tool(
            server, "season_comparison",
            {"competition": "Serie A", "season_a": 2018, "season_b": 2019},
        )
        assert "2018" in text and "2019" in text
        assert "Palmeiras" in text and "Flamengo" in text


class TestErrorHandling:
    """Scenario: Graceful errors over MCP
        Given the MCP server is running
        When I call a tool with an unknown or ambiguous team
        Then I should receive a helpful message instead of a crash
    """

    def test_given_unknown_team_when_calling_search_matches_then_helpful_message(self, server):
        text = call_tool(server, "search_matches", {"team": "Hogwarts FC"})
        assert "not found" in text.lower()

    def test_given_ambiguous_team_when_calling_search_matches_then_candidates_listed(self, server):
        text = call_tool(server, "search_matches", {"team": "atletico"})
        assert "Ambiguous" in text
        assert "Athletico-PR" in text

    def test_given_unknown_competition_when_calling_standings_then_error_message(self, server):
        text = call_tool(server, "standings", {"competition": "NBA", "season": 2019})
        assert "not found" in text.lower()

    def test_given_bad_arguments_when_calling_tool_then_protocol_error(self, server):
        from mcp.server.mcpserver.exceptions import ToolError
        with pytest.raises(ToolError):
            asyncio.run(server.call_tool("search_matches", {"season": "not-a-year"}))


class TestPerformance:
    """Scenario: Query performance
        Given the loaded dataset
        When I run simple lookups and aggregate queries
        Then they should respond within the specification's time budget
    """

    def test_given_simple_lookup_then_under_two_seconds(self, server):
        import time
        start = time.monotonic()
        call_tool(server, "last_match_between", {"team_a": "Flamengo", "team_b": "Corinthians"})
        elapsed = time.monotonic() - start
        assert elapsed < 2.0

    def test_given_aggregate_query_then_under_five_seconds(self, server):
        import time
        start = time.monotonic()
        call_tool(server, "standings", {"competition": "Serie A", "season": 2019})
        call_tool(server, "average_goals", {"competition": "Serie A"})
        elapsed = time.monotonic() - start
        assert elapsed < 5.0
