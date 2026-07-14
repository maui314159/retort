"""Tests for the MCP server tool wrappers.

The tools return formatted text; these tests assert the text is non-empty,
well-formed and reflects the underlying query results.
"""

from __future__ import annotations

import pytest

from brazilian_soccer import server as S
from brazilian_soccer import queries as Q


def test_tools_registered():
    tools = set(S.mcp._tool_manager._tools.keys())
    expected = {
        "search_matches", "last_match_between", "head_to_head",
        "get_team_stats", "team_competitions", "competition_standings",
        "competition_champion", "biggest_wins", "average_goals",
        "best_record", "derby_matches", "search_players", "top_players",
        "players_at_club", "match_statistics", "list_teams",
        "list_competitions",
    }
    assert expected <= tools, expected - tools


def test_head_to_head_tool_format():
    out = S.head_to_head("Flamengo", "Fluminense")
    assert "Flamengo" in out and "Fluminense" in out
    assert "wins" in out and "Matches:" in out


def test_champion_tool():
    out = S.competition_champion("Brasileirão", 2019)
    assert "Flamengo" in out
    assert "90 pts" in out


def test_standings_tool_champion_marker():
    out = S.competition_standings("Brasileirão", 2018, top=5)
    assert "Champion" in out
    assert "Palmeiras" in out


def test_average_goals_tool():
    out = S.average_goals(competition="Brasileirão", season=2019)
    assert "Average goals per match" in out
    assert "Home win rate" in out


def test_biggest_wins_tool():
    out = S.biggest_wins(limit=3)
    assert "Biggest victories" in out
    # Each line reports a margin.
    assert "margin" in out


def test_search_players_tool():
    out = S.search_players(nationality="Brazil", limit=3)
    assert "Overall" in out
    assert "Brazil" in out


def test_get_team_stats_tool_home_away():
    out = S.get_team_stats("Corinthians", season=2022)
    assert "Home:" in out and "Away:" in out
    assert "Win rate" in out


def test_list_competitions_tool():
    out = S.list_competitions()
    assert "Brasileirão Serie A" in out
    assert "Copa Libertadores" in out


def test_empty_result_messages():
    assert "No matches" in S.search_matches(team="Palmeiras", season=1900)
    assert "No players" in S.search_players(name="ZZZNoSuchPlayer")


def test_derby_matches_tool_labels():
    out = S.derby_matches(season=2023)
    assert "derby" in out.lower() or "Fla-Flu" in out
