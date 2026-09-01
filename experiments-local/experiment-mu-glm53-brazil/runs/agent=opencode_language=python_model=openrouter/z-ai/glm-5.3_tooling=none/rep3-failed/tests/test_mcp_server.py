"""BDD scenarios for the MCP server surface.

Feature: MCP Server
  The MCP server exposes the query engine as tools over the Model
  Context Protocol.  Every tool must answer with well-formed text.
"""

from __future__ import annotations

import asyncio

import pytest

EXPECTED_TOOLS = {
    "list_competitions",
    "find_team",
    "list_teams",
    "search_matches",
    "head_to_head",
    "team_stats",
    "standings",
    "search_players",
    "club_players",
    "statistics",
    "biggest_wins",
    "derbies",
}


def _call(server, tool: str, arguments: dict) -> str:
    result = asyncio.run(server.call_tool(tool, arguments))
    assert not result.is_error, f"tool {tool} failed: {result}"
    return result.content[0].text


@pytest.fixture(scope="module")
def server(engine):
    from brazilian_soccer_mcp.server import build_server

    return build_server(engine=engine)


class TestToolDiscovery:
    """
    Scenario: An MCP client discovers the available tools
      Given the MCP server is running
      When the client lists tools
      Then all query capabilities are exposed
    """

    def test_when_listing_tools_then_all_capabilities_are_exposed(self, server):
        tools = asyncio.run(server.list_tools())
        names = {tool.name for tool in tools}
        assert EXPECTED_TOOLS <= names
        assert len(names) == len(EXPECTED_TOOLS)

    def test_when_listing_tools_then_every_tool_has_a_description(self, server):
        tools = asyncio.run(server.list_tools())
        for tool in tools:
            assert tool.description and len(tool.description) > 20


class TestMatchTools:
    """
    Scenario: The client asks for Flamengo vs Fluminense matches
      Given the MCP server is running
      When the client calls search_matches
      Then the answer lists matches with dates and scores
    """

    def test_when_calling_search_matches_then_matches_are_formatted(self, server):
        text = _call(
            server,
            "search_matches",
            {"team": "Flamengo", "opponent": "Fluminense", "limit": 3},
        )
        assert "Flamengo vs Fluminense" in text
        assert "more matches in dataset" in text
        assert "(" in text and "-" in text

    def test_when_calling_search_matches_with_a_stage_then_finals_are_found(self, server):
        text = _call(
            server,
            "search_matches",
            {"competition": "Libertadores", "season": 2019, "stage": "final"},
        )
        assert "Flamengo" in text
        assert "2-1" in text

    def test_when_calling_search_matches_with_an_unknown_team_then_help_is_returned(self, server):
        text = _call(server, "search_matches", {"team": "Nyselfc"}),
        text = text[0] if isinstance(text, tuple) else text
        assert "Team not found" in text


class TestHeadToHeadTool:
    """
    Scenario: The client asks for a head-to-head comparison
      Given the MCP server is running
      When the client calls head_to_head
      Then the answer includes the aggregate record
    """

    def test_when_calling_head_to_head_then_the_record_is_summarised(self, server):
        text = _call(
            server,
            "head_to_head",
            {"team_a": "Flamengo", "team_b": "Fluminense", "limit": 3},
        )
        assert "Fla-Flu" in text
        assert "Head-to-head in dataset:" in text
        assert "wins" in text


class TestTeamAndStandingsTools:
    """
    Scenario: The client asks for team stats and standings
      Given the MCP server is running
      When the client calls team_stats and standings
      Then records and tables are returned as text
    """

    def test_when_calling_team_stats_then_the_record_is_formatted(self, server):
        text = _call(
            server,
            "team_stats",
            {
                "team": "Corinthians",
                "season": 2022,
                "competition": "Série A",
                "venue": "home",
            },
        )
        assert "Corinthians" in text
        assert "Wins: 12, Draws: 4, Losses: 3" in text
        assert "Win rate: 63.2%" in text

    def test_when_calling_standings_then_the_table_and_champion_are_returned(self, server):
        text = _call(server, "standings", {"season": 2019})
        assert "1. Flamengo - 90 pts (28W, 6D, 4L" in text
        assert "Champion: Flamengo" in text
        assert "Relegated" in text

    def test_when_calling_standings_for_serie_b_then_the_table_is_returned(self, server):
        text = _call(
            server, "standings", {"season": 2023, "competition": "Série B"}
        )
        assert "Série B 2023 standings" in text
        assert "Champion:" in text


class TestPlayerTools:
    """
    Scenario: The client asks about players
      Given the MCP server is running
      When the client calls search_players and club_players
      Then player lists with ratings are returned
    """

    def test_when_calling_search_players_then_brazilians_are_ranked(self, server):
        text = _call(
            server, "search_players", {"nationality": "Brazilian", "limit": 5}
        )
        assert "Neymar Jr" in text
        assert "Overall: 92" in text

    def test_when_calling_club_players_then_the_roster_is_returned(self, server):
        text = _call(server, "club_players", {"club": "Fluminense"})
        assert "Fluminense players" in text
        assert "average rating" in text

    def test_when_calling_search_players_for_an_unknown_name_then_suggestions_come_back(self, server):
        text = _call(server, "search_players", {"name": "Gabriel Barbosa"})
        assert "Team not found" in text
        assert "Gabriel" in text


class TestStatisticsAndDerbyTools:
    """
    Scenario: The client asks for statistics and derbies
      Given the MCP server is running
      When the client calls statistics, biggest_wins and derbies
      Then aggregate answers are returned
    """

    def test_when_calling_statistics_then_aggregates_are_returned(self, server):
        text = _call(
            server, "statistics", {"competition": "Série A", "season": 2019}
        )
        assert "Average goals per match: 2.31" in text
        assert "Home wins" in text

    def test_when_calling_biggest_wins_then_margins_are_listed(self, server):
        text = _call(server, "biggest_wins", {"competition": "Libertadores", "limit": 3})
        assert "River Plate" in text
        assert "8-0" in text

    def test_when_calling_derbies_then_classics_are_listed(self, server):
        text = _call(server, "derbies", {"derby": "Gre-Nal", "limit": 2})
        assert "Gre-Nal" in text
        assert "Record:" in text

    def test_when_calling_find_team_then_the_resolution_is_reported(self, server):
        text = _call(server, "find_team", {"name": "Timão"})
        assert "Corinthians" in text
        assert "Matches in dataset" in text

    def test_when_calling_list_competitions_then_all_competitions_appear(self, server):
        text = _call(server, "list_competitions", {})
        for competition in (
            "Brasileirão Série A",
            "Copa do Brasil",
            "Copa Libertadores",
        ):
            assert competition in text
