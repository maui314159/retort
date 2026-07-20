"""Tests for the MCP server layer: tool registration and text output."""

from __future__ import annotations

import asyncio

import pytest

from brazilian_soccer_mcp import server

EXPECTED_TOOLS = {
    "find_matches",
    "head_to_head",
    "team_stats",
    "league_standings",
    "search_players",
    "club_players",
    "biggest_wins",
    "competition_statistics",
    "list_competitions",
    "list_teams",
    "dataset_summary",
}


def test_all_tools_registered():
    tools = asyncio.run(server.mcp.list_tools())
    names = {tool.name for tool in tools}
    assert EXPECTED_TOOLS <= names


def test_tools_have_descriptions():
    for tool in asyncio.run(server.mcp.list_tools()):
        assert tool.description, f"{tool.name} is missing a description"


def test_find_matches_tool_text():
    text = server.find_matches(team="Flamengo", opponent="Corinthians", limit=3)
    assert "Flamengo" in text and "Corinthians" in text
    assert "Brasileirão" in text


def test_head_to_head_tool_text():
    text = server.head_to_head("Flamengo", "Fluminense")
    assert "Head-to-head in dataset" in text
    assert "wins" in text and "draws" in text


def test_team_stats_tool_text():
    text = server.team_stats("Corinthians", season=2022, venue="home",
                             competition="Brasileirão")
    assert "Matches: 19" in text
    assert "Win rate:" in text


def test_league_standings_tool_text():
    text = server.league_standings(2019)
    assert "Flamengo - 90 pts" in text
    assert "Champion" in text
    assert "Relegated" in text


def test_search_players_tool_text():
    text = server.search_players(name="Neymar")
    assert "Neymar Jr" in text
    assert "Overall: 92" in text


def test_biggest_wins_tool_text():
    text = server.biggest_wins(competition="Brasileirão Série A", limit=3)
    assert "Biggest victories" in text
    assert "7-0" in text or "0-7" in text


def test_competition_statistics_tool_text():
    text = server.competition_statistics(competition="Brasileirão Série A", season=2019)
    assert "Average goals per match" in text
    assert "Home win rate" in text


def test_unknown_team_returns_friendly_message():
    text = server.find_matches(team="Flamengooo")
    assert "Unknown team" in text
    assert "Flamengo" in text  # suggestion included


def test_dataset_summary_tool_text():
    text = server.dataset_summary()
    assert "Total matches" in text
    assert "fifa_data.csv" in text


@pytest.mark.parametrize("tool_name", sorted(EXPECTED_TOOLS))
def test_tool_callable(tool_name):
    assert callable(getattr(server, tool_name))
