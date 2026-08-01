"""Integration tests for the MCP server (in-memory FastMCP client)."""

from __future__ import annotations

import pytest
from fastmcp import Client

from soccer_mcp.mcp_server import TOOL_FUNCTIONS, create_server
from soccer_mcp.tools_api import (
    dataset_summary,
    head_to_head,
    list_competitions,
    player_profile,
    search_matches,
    search_players,
    standings,
    team_stats,
)

EXPECTED_TOOLS = {fn.__name__ for fn in TOOL_FUNCTIONS}


@pytest.fixture
def server():
    return create_server()


@pytest.mark.asyncio
class TestMCPServer:
    async def test_all_tools_registered(self, server):
        async with Client(server) as client:
            tools = await client.list_tools()
            names = {t.name for t in tools}
        assert EXPECTED_TOOLS <= names
        assert len(names) >= 15

    async def test_tools_have_descriptions(self, server):
        async with Client(server) as client:
            tools = await client.list_tools()
        for tool in tools:
            assert tool.description, f"{tool.name} missing description"

    async def test_call_head_to_head(self, server):
        async with Client(server) as client:
            result = await client.call_tool(
                "head_to_head", {"team1": "Flamengo", "team2": "Fluminense"}
            )
        text = result.content[0].text
        assert "Fla-Flu" in text
        assert "Head-to-head" in text

    async def test_call_standings(self, server):
        async with Client(server) as client:
            result = await client.call_tool(
                "standings", {"season": 2019, "competition": "brasileirao"}
            )
        text = result.content[0].text
        assert "Flamengo - 90 pts" in text
        assert "Champion" in text

    async def test_call_search_players(self, server):
        async with Client(server) as client:
            result = await client.call_tool(
                "search_players", {"name": "Neymar"}
            )
        assert "Neymar Jr" in result.content[0].text

    async def test_call_team_stats(self, server):
        async with Client(server) as client:
            result = await client.call_tool(
                "team_stats",
                {"team": "Corinthians", "season": 2022, "venue": "home"},
            )
        assert "Win rate" in result.content[0].text

    async def test_unknown_team_returns_error_message(self, server):
        async with Client(server) as client:
            result = await client.call_tool(
                "head_to_head",
                {"team1": "Flamengo", "team2": "Not A Real Club FC"},
                raise_on_error=False,
            )
        assert result.is_error
        assert "Unknown team" in result.content[0].text


class TestToolsApiDirect:
    """The same functions callable without any MCP transport."""

    def test_search_matches_text(self):
        text = search_matches(team="Flamengo", opponent="Fluminense", limit=5)
        assert "Flamengo" in text and "Fluminense" in text

    def test_dataset_summary_mentions_all_files(self):
        text = dataset_summary()
        for name in ("Brasileirao_Matches.csv", "Brazilian_Cup_Matches.csv",
                     "Libertadores_Matches.csv", "BR-Football-Dataset.csv",
                     "novo_campeonato_brasileiro.csv", "fifa_data.csv"):
            assert name in text

    def test_list_competitions_text(self):
        assert "Copa Libertadores" in list_competitions()

    def test_player_profile_text(self):
        text = player_profile("Neymar")
        assert "Neymar Jr" in text
        assert "Overall: 92" in text
