"""
Unit tests for the MCP server tool wrappers.
"""

from __future__ import annotations

import server


def test_find_matches_tool():
    text = server.find_matches("Flamengo", "Fluminense", season=2023, limit=2)
    assert "Flamengo" in text
    assert "Fluminense" in text
    assert "2023" in text


def test_team_statistics_tool():
    text = server.team_statistics("Palmeiras", season=2022)
    assert "Palmeiras" in text
    assert "Matches:" in text
    assert "Win rate:" in text


def test_find_players_tool():
    text = server.find_players(nationality="Brazil", limit=3)
    assert "Neymar" in text or "Brazil" in text
    assert "Overall:" in text


def test_competition_standings_tool():
    text = server.competition_standings("Brasileirão", 2023)
    assert "Grêmio" in text or "Palmeiras" in text
    assert "pts" in text


def test_goals_summary_tool():
    text = server.goals_summary("Brasileirão", 2023)
    assert "Average goals per match:" in text
    assert "Total matches:" in text
