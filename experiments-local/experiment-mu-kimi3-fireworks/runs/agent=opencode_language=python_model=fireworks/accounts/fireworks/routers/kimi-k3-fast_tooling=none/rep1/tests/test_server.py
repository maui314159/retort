"""Integration tests for the MCP server (FastMCP in-memory client)."""

from __future__ import annotations

import pytest
from fastmcp import Client

from brazilian_soccer_mcp.server import mcp

EXPECTED_TOOLS = {
    "find_matches",
    "last_match",
    "head_to_head",
    "team_statistics",
    "team_competitions",
    "search_players",
    "player_profile",
    "club_roster",
    "competition_standings",
    "competition_schedule",
    "biggest_victories",
    "competition_overview",
    "top_scoring_teams",
    "compare_seasons",
    "dataset_info",
    "list_teams",
}


async def call(tool: str, **args) -> str:
    async with Client(mcp) as client:
        result = await client.call_tool(tool, args)
        assert not result.is_error, f"{tool} returned an MCP error"
        return result.content[0].text


async def test_server_lists_all_tools():
    async with Client(mcp) as client:
        tools = await client.list_tools()
    names = {t.name for t in tools}
    assert EXPECTED_TOOLS <= names
    for t in tools:
        assert t.description, f"tool {t.name} lacks a description"


async def test_dataset_info():
    text = await call("dataset_info")
    assert "Matches" in text
    assert "FIFA players" in text
    assert "Brasileirão Série A" in text
    assert "Copa do Brasil" in text
    assert "Copa Libertadores" in text


async def test_find_matches_fla_flu():
    text = await call("find_matches", team="Flamengo", versus="Fluminense", limit=5)
    assert "Flamengo" in text and "Fluminense" in text
    assert "match(es) in dataset" in text
    # Spec answer format: "- <date>: <home> <hg>-<ag> <away>"
    assert "- 20" in text and ":" in text


async def test_find_matches_unknown_team():
    text = await call("find_matches", team="Wakanda United")
    assert "Unknown team" in text


async def test_last_match_tool():
    text = await call("last_match", team1="Flamengo", team2="Corinthians")
    assert "Most recent Flamengo vs Corinthians" in text
    assert "[" in text  # competition suffix


async def test_head_to_head_tool():
    text = await call("head_to_head", team1="Palmeiras", team2="Santos")
    assert "head-to-head" in text.lower()
    assert "wins" in text and "draws" in text


async def test_team_statistics_tool():
    text = await call("team_statistics", team="Corinthians", season=2022, venue="home")
    assert "Corinthians home record (2022" in text
    assert "Matches:" in text
    assert "Wins:" in text and "Draws:" in text and "Losses:" in text
    assert "Goals For:" in text and "Goals Against:" in text
    assert "Win rate:" in text


async def test_team_competitions_tool():
    text = await call("team_competitions", team="Palmeiras")
    assert "Brasileirão Série A" in text
    assert "Copa do Brasil" in text
    assert "Copa Libertadores" in text


async def test_search_players_brazilians():
    text = await call("search_players", nationality="Brazil", limit=5)
    assert "Neymar Jr" in text
    assert "Overall: 92" in text


async def test_search_players_by_club():
    text = await call("search_players", club="Grêmio", limit=25)
    assert "Grêmio" in text


async def test_player_profile_tool():
    text = await call("player_profile", name="Neymar")
    assert "Neymar Jr (Brazil)" in text
    assert "Overall: 92" in text
    assert "Paris Saint-Germain" in text


async def test_player_profile_not_found():
    text = await call("player_profile", name="Zzyzzy Unknown")
    assert "No player found" in text


async def test_club_roster_tool():
    text = await call("club_roster", club="Fluminense", nationality="Brazil")
    assert "Fluminense squad" in text
    assert "avg rating" in text


async def test_standings_tool_2019():
    text = await call("competition_standings", season=2019)
    assert "2019 Brasileirão Série A Standings" in text
    assert "Flamengo - 90 pts (28W, 6D, 4L)" in text
    assert "Champion" in text
    assert "Relegated:" in text


async def test_competition_schedule_tool():
    text = await call("competition_schedule", competition="Copa Libertadores", season=2018)
    assert "Copa Libertadores 2018" in text
    assert "Stages present:" in text
    assert "final" in text


async def test_biggest_victories_tool():
    text = await call("biggest_victories", limit=5)
    assert "Biggest victories" in text
    assert "1. " in text


async def test_competition_overview_tool():
    text = await call("competition_overview", competition="Brasileirão Série A")
    assert "Average goals per match:" in text
    assert "Home win rate:" in text


async def test_top_scoring_teams_tool():
    text = await call("top_scoring_teams", season=2019, competition="Serie A")
    assert "Flamengo" in text


async def test_compare_seasons_tool():
    text = await call("compare_seasons", season_a=2018, season_b=2019)
    assert "2018" in text and "2019" in text
    assert "Avg goals per match" in text


async def test_list_teams_tool():
    text = await call("list_teams", contains="Fla")
    assert "Flamengo" in text


async def test_stdio_transport_end_to_end():
    """The server runs as a real subprocess: python -m brazilian_soccer_mcp."""
    import sys

    from fastmcp.client.transports import StdioTransport

    transport = StdioTransport(command=sys.executable, args=["-m", "brazilian_soccer_mcp"])
    async with Client(transport) as client:
        tools = await client.list_tools()
        assert EXPECTED_TOOLS <= {t.name for t in tools}
        result = await client.call_tool("last_match", {"team1": "Flamengo", "team2": "Corinthians"})
        assert "Most recent" in result.content[0].text
