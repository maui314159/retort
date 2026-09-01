"""BDD scenarios for the MCP server protocol layer and query performance.

Feature: MCP server
  Scenario: Tools are exposed over MCP
    Given the server is built
    When tools are listed
    Then all documented tools are available
    And calling a tool returns MCP content

Performance scenarios implement the TASK.md budget: simple lookups
respond in under 2 seconds, aggregate queries in under 5 seconds.
"""

from __future__ import annotations

import asyncio
import json
import time

import server as server_module
from server import (
    get_aggregate_statistics,
    get_best_records,
    get_head_to_head,
    get_standings,
    get_team_stats,
    search_matches,
    search_players,
)

EXPECTED_TOOLS = {
    "get_dataset_overview",
    "resolve_team",
    "list_teams",
    "search_matches",
    "get_head_to_head",
    "get_team_stats",
    "search_players",
    "get_player_details",
    "get_club_players",
    "get_standings",
    "get_competition_info",
    "get_competition_finals",
    "get_aggregate_statistics",
    "get_biggest_wins",
    "get_best_records",
    "get_derby_matches",
}


def _call_tool(name: str, arguments: dict) -> dict:
    """Invoke a tool through the MCP server and decode its JSON content."""
    result = asyncio.run(server_module.app.call_tool(name, arguments))
    assert not result.is_error, result
    assert result.content, "tool must return content"
    return json.loads(result.content[0].text)


class TestMcpToolSurface:
    """Scenarios: the MCP tool listing."""

    def test_all_documented_tools_are_registered(self):
        """
        Scenario: tool registry
          Given the server is built
          When tools are listed
          Then all 16 documented tools are exposed
        """
        tools = asyncio.run(server_module.app.list_tools())
        names = {tool.name for tool in tools}
        assert EXPECTED_TOOLS <= names

    def test_tools_carry_descriptions(self):
        """
        Scenario: tool descriptions guide the LLM
          Given the registered tools
          When listed
          Then every tool has a non-empty description
        """
        tools = asyncio.run(server_module.app.list_tools())
        assert all(tool.description.strip() for tool in tools)

    def test_call_search_matches_via_mcp(self):
        """
        Scenario: calling a match query over MCP
          Given the MCP server
          When search_matches is called with team "Flamengo"
          Then structured JSON content comes back
        """
        payload = _call_tool("search_matches", {"team": "Flamengo", "limit": 5})
        assert payload["data"]["total_matches"] > 100
        assert len(payload["data"]["matches"]) == 5

    def test_call_get_standings_via_mcp(self):
        """
        Scenario: calling standings over MCP
          Given the MCP server
          When get_standings is called for the 2019 Brasileirão
          Then Flamengo is returned as champion
        """
        payload = _call_tool(
            "get_standings",
            {"competition": "Brasileirão Série A", "season": 2019},
        )
        assert payload["data"]["champion"] == "Flamengo"

    def test_call_player_search_via_mcp(self):
        """
        Scenario: calling a player query over MCP
          Given the MCP server
          When search_players is called for Brazil
          Then Brazilian players are returned
        """
        payload = _call_tool(
            "search_players", {"nationality": "Brazil", "min_overall": 90}
        )
        assert payload["data"]["count"] >= 1
        assert payload["data"]["players"][0]["name"] == "Neymar Jr"

    def test_error_results_are_structured(self):
        """
        Scenario: graceful failures over MCP
          Given an unknown team
          When search_matches is called
          Then the error payload is JSON, not a crash
        """
        payload = _call_tool("search_matches", {"team": "Hogwarts Quidditch"})
        assert "error" in payload


class TestQueryPerformance:
    """Scenarios: TASK.md performance budget."""

    def test_simple_lookup_under_2_seconds(self, data):
        """
        Scenario: simple lookup budget
          Given warm data
          When a team match lookup runs
          Then it completes in under 2 seconds
        """
        start = time.perf_counter()
        result = search_matches(team="Flamengo", opponent="Fluminense", limit=25)
        elapsed = time.perf_counter() - start
        assert result["data"]["total_matches"] > 0
        assert elapsed < 2.0

    def test_player_lookup_under_2_seconds(self, data):
        """
        Scenario: player lookup budget
          Given warm data
          When a player search runs
          Then it completes in under 2 seconds
        """
        start = time.perf_counter()
        result = search_players(nationality="Brazil", limit=25)
        elapsed = time.perf_counter() - start
        assert result["data"]["count"] > 500
        assert elapsed < 2.0

    def test_aggregate_query_under_5_seconds(self, data):
        """
        Scenario: aggregate budget
          Given warm data
          When a full-league standings calculation runs
          Then it completes in under 5 seconds
        """
        start = time.perf_counter()
        result = get_standings(competition="Brasileirão", season=2022)
        elapsed = time.perf_counter() - start
        assert len(result["data"]["table"]) == 20
        assert elapsed < 5.0

    def test_heavy_composite_query_under_5_seconds(self, data):
        """
        Scenario: composite analysis budget
          Given warm data
          When head-to-head, records and aggregates run together
          Then the whole batch completes in under 5 seconds
        """
        start = time.perf_counter()
        get_head_to_head("Palmeiras", "Santos")
        get_best_records(competition="Serie A", season=2019, venue="home")
        get_aggregate_statistics(competition="Serie A")
        get_team_stats(team="Corinthians", season=2022, venue="home")
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0
