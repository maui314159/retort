"""
BDD scenarios: MCP server integration (in-memory client session).

Feature: MCP server
  Scenario: An LLM client discovers and calls the tools
    Given the MCP server is running over the shared service
    When the client lists tools
    Then all capability families from TASK.md are exposed
    And calling a tool returns the formatted answer text
"""

from __future__ import annotations

import pytest

from mcp.client._memory import InMemoryTransport
from mcp.client.session import ClientSession

EXPECTED_TOOLS = {
    # match queries
    "search_matches", "head_to_head", "finals",
    # team queries
    "team_record", "team_overview",
    # competition queries
    "standings", "champion", "relegated",
    # statistical analysis
    "competition_stats", "biggest_wins", "best_records", "derbies",
    "compare_seasons",
    # player queries
    "search_players", "player_profile", "club_squad",
    "top_brazilian_players", "brazilians_at_brazilian_clubs",
    # discovery
    "list_competitions", "list_seasons",
}


@pytest.fixture(scope="module")
async def mcp_session(mcp_server, anyio_backend):
    """A connected MCP client session backed by an in-memory transport."""
    async with InMemoryTransport(mcp_server) as transport:
        async with ClientSession(transport[0], transport[1]) as session:
            await session.initialize()
            yield session


class TestToolDiscovery:
    """Scenario: the LLM client discovers the tool surface."""

    async def test_all_expected_tools_registered(self, mcp_session):
        tools = await mcp_session.list_tools()
        names = {tool.name for tool in tools.tools}
        # Then every capability family from TASK.md is represented
        assert EXPECTED_TOOLS <= names
        assert len(names) == 20

    async def test_tools_have_descriptions(self, mcp_session):
        tools = await mcp_session.list_tools()
        for tool in tools.tools:
            assert tool.description, f"tool {tool.name} lacks a description"


class TestToolCalls:
    """Scenario: calling tools returns spec-style answer text."""

    async def _call(self, session, name, arguments):
        result = await session.call_tool(name, arguments)
        assert not result.is_error, f"tool {name} returned an error"
        return result.content[0].text

    async def test_standings_tool(self, mcp_session):
        # When I call standings for the 2019 Brasileirão
        text = await self._call(
            mcp_session, "standings", {"competition": "brasileirao", "season": 2019}
        )
        # Then the answer matches TASK.md's example format
        assert "1. Flamengo - 90 pts (28W, 6D, 4L" in text
        assert "- Champion" in text

    async def test_champion_tool(self, mcp_session):
        text = await self._call(
            mcp_session, "champion", {"competition": "libertadores", "season": 2019}
        )
        assert "Champion: Flamengo" in text

    async def test_head_to_head_tool(self, mcp_session):
        text = await self._call(
            mcp_session, "head_to_head", {"team_a": "Flamengo", "team_b": "Fluminense"}
        )
        assert "Head-to-head in dataset: Flamengo 18 wins" in text

    async def test_search_matches_tool_with_date_range(self, mcp_session):
        text = await self._call(
            mcp_session,
            "search_matches",
            {
                "team": "Palmeiras",
                "date_from": "2023-08-01",
                "date_to": "2023-09-30",
                "limit": 10,
            },
        )
        assert "Matches involving Palmeiras" in text
        assert "2023-08-14: Palmeiras 1-0 Cruzeiro" in text

    async def test_search_players_tool(self, mcp_session):
        text = await self._call(
            mcp_session, "search_players", {"nationality": "Brazil", "min_overall": 90}
        )
        assert "Neymar Jr - Overall: 92" in text

    async def test_club_squad_tool(self, mcp_session):
        text = await self._call(mcp_session, "club_squad", {"club": "Santos"})
        assert "20 players" in text

    async def test_derbies_tool(self, mcp_session):
        text = await self._call(mcp_session, "derbies", {"season": 2023})
        assert "Grenal" in text

    async def test_relegated_tool(self, mcp_session):
        text = await self._call(
            mcp_session, "relegated", {"competition": "brasileirao", "season": 2020}
        )
        assert "Botafogo" in text

    async def test_list_competitions_tool(self, mcp_session):
        text = await self._call(mcp_session, "list_competitions", {})
        for competition in (
            "Brasileirão Série A",
            "Copa do Brasil",
            "Copa Libertadores",
        ):
            assert competition in text

    async def test_team_record_tool(self, mcp_session):
        text = await self._call(
            mcp_session,
            "team_record",
            {
                "team": "Corinthians",
                "season": 2022,
                "competition": "brasileirao",
                "venue": "home",
            },
        )
        assert "- Matches: 15" in text
        assert "- Win rate: 66.7%" in text

    async def test_biggest_wins_tool(self, mcp_session):
        text = await self._call(
            mcp_session, "biggest_wins", {"competition": "libertadores", "limit": 3}
        )
        assert "8-0" in text


class TestToolErrorHandling:
    """Scenario: bad input produces guidance, not crashes."""

    @pytest.mark.parametrize(
        ("tool", "arguments"),
        [
            ("search_matches", {"team": "ZZZ Not A Team"}),
            ("search_matches", {"competition": "NBA"}),
            ("champion", {"competition": "World Cup"}),
            ("player_profile", {"name": "Gabriel Barbosa"}),
            ("team_record", {"team": "Corinthians", "venue": "neutral"}),
        ],
    )
    async def test_bad_input_returns_helpful_text(self, mcp_session, tool, arguments):
        result = await mcp_session.call_tool(tool, arguments)
        assert not result.is_error
        text = result.content[0].text
        # Then the tool explains what went wrong instead of failing
        assert any(
            marker in text
            for marker in ("Could not answer", "No ", "not found", "Try")
        ) or "not found" in text.lower()
