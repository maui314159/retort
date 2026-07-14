"""
test_server.py
==============

Unit tests for the MCP server tool wrappers.

These tests call each MCP tool function directly and assert on the
human-readable text it returns.  They are intentionally separate from
the BDD feature tests, which target the underlying query engine.
"""

from __future__ import annotations

import asyncio
import json

import pytest

import data_loader
import server


@pytest.fixture(autouse=True)
def _reset_loader_cache() -> None:
    data_loader.clear_cache()
    yield
    data_loader.clear_cache()


# ---------------------------------------------------------------------------
# find_matches
# ---------------------------------------------------------------------------


def test_find_matches_two_teams():
    text = server.find_matches("Flamengo", "Fluminense", season=2023, limit=3)
    assert "Flamengo" in text
    assert "Fluminense" in text
    assert "2023" in text
    assert "Brasileirão" in text


def test_find_matches_no_results_returns_friendly_text():
    text = server.find_matches("Nonexistent FC")
    # The tool surfaces a "could not resolve" message when the team
    # lookup fails, which is the expected friendly behaviour.
    assert text
    assert "Could not resolve" in text or "No matches" in text


def test_find_matches_invalid_competition():
    text = server.find_matches(competition="Some Cup")
    assert "Could not resolve" in text or "No matches" in text


# ---------------------------------------------------------------------------
# team_statistics
# ---------------------------------------------------------------------------


def test_team_statistics_palmeiras_2022():
    text = server.team_statistics("Palmeiras", season=2022)
    assert "Palmeiras" in text
    assert "Matches:" in text
    assert "Win rate:" in text


def test_team_statistics_unknown_team():
    text = server.team_statistics("Nonexistent FC")
    assert "Could not resolve" in text


# ---------------------------------------------------------------------------
# head_to_head
# ---------------------------------------------------------------------------


def test_head_to_head_renders_summary():
    text = server.head_to_head("Flamengo", "Fluminense", season=2023)
    assert "Flamengo" in text
    assert "Fluminense" in text
    assert "wins" in text.lower()


# ---------------------------------------------------------------------------
# find_players
# ---------------------------------------------------------------------------


def test_find_players_brazilian():
    text = server.find_players(nationality="Brazil", limit=3)
    assert "Neymar" in text or "Brazil" in text
    assert "Overall:" in text


def test_find_players_club_real_madrid():
    text = server.find_players(club="Real Madrid", limit=3)
    assert "Real Madrid" in text
    assert "Overall:" in text


# ---------------------------------------------------------------------------
# competition_standings
# ---------------------------------------------------------------------------


def test_competition_standings_2019():
    text = server.competition_standings("Brasileirão", 2019)
    assert "Flamengo" in text
    assert "pts" in text


def test_competition_standings_no_data():
    text = server.competition_standings("Brasileirão", 1900)
    assert "No matches" in text or "No standings" in text


# ---------------------------------------------------------------------------
# biggest_wins
# ---------------------------------------------------------------------------


def test_biggest_wins_2022():
    text = server.biggest_wins("Brasileirão", 2022, limit=3)
    assert "biggest wins" in text.lower() or "Biggest" in text


# ---------------------------------------------------------------------------
# goals_summary
# ---------------------------------------------------------------------------


def test_goals_summary_renders_metrics():
    text = server.goals_summary("Brasileirão", 2023)
    assert "Average goals per match:" in text
    assert "Total matches:" in text
    assert "Home wins:" in text


# ---------------------------------------------------------------------------
# top_scoring_teams
# ---------------------------------------------------------------------------


def test_top_scoring_teams_renders_ranking():
    text = server.top_scoring_teams("Brasileirão", 2023, limit=3)
    assert "Top scoring teams" in text
    assert "goals" in text


# ---------------------------------------------------------------------------
# relegated_teams
# ---------------------------------------------------------------------------


def test_relegated_teams_2019():
    text = server.relegated_teams(2019)
    assert "Relegated" in text
    assert "Avai" in text or "Chapecoense" in text


def test_relegated_teams_no_data():
    text = server.relegated_teams(1900)
    assert text
    assert "No data" in text or "No matches" in text or "No Brasileirão" in text


# ---------------------------------------------------------------------------
# team_competition_history
# ---------------------------------------------------------------------------


def test_team_competition_history_flamengo():
    text = server.team_competition_history("Flamengo")
    assert "Flamengo" in text
    assert "Brasileirão" in text


# ---------------------------------------------------------------------------
# brazilian_club_summary
# ---------------------------------------------------------------------------


def test_brazilian_club_summary_renders():
    text = server.brazilian_club_summary()
    assert "Brazilian clubs" in text
    assert "Santos" in text


# ---------------------------------------------------------------------------
# raw_query
# ---------------------------------------------------------------------------


def test_raw_query_dispatches_to_correct_tool():
    raw = server.raw_query(
        "find_matches",
        {"team": "Flamengo", "opponent": "Fluminense", "season": 2023, "limit": 2},
    )
    payload = json.loads(raw)
    assert payload["count"] > 0
    assert isinstance(payload["matches"], list)


def test_raw_query_unknown_tool_returns_error():
    raw = server.raw_query("nope", {})
    payload = json.loads(raw)
    assert "error" in payload
    assert "available" in payload


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


def test_all_expected_tools_registered():
    tools = asyncio.run(server.mcp.list_tools())
    names = {t.name for t in tools}
    expected = {
        "find_matches",
        "team_statistics",
        "head_to_head",
        "find_players",
        "competition_standings",
        "biggest_wins",
        "goals_summary",
        "top_scoring_teams",
        "relegated_teams",
        "team_competition_history",
        "brazilian_club_summary",
        "raw_query",
    }
    assert expected.issubset(names), f"Missing: {expected - names}"
