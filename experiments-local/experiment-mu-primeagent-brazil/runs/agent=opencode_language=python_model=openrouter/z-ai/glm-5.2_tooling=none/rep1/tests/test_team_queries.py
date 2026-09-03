"""BDD tests for team queries.

Feature: Team Queries

  Scenario: Get team statistics for a season
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season 2022
    Then I should receive wins, losses, draws and goals

  Scenario: Compare two teams
    Given the match data is loaded
    When I compare "Palmeiras" and "Santos"
    Then I should receive both teams' records and a head-to-head block

  Scenario: List competitions a team has appeared in
    Given the match data is loaded
    When I request the competitions for "Flamengo"
    Then I should receive a list of competitions with match counts
"""

from __future__ import annotations

from brazilian_soccer_mcp.queries import (
    compare_teams,
    competitions_for_team,
    team_stats,
)


def test_team_stats_palmeiras_2022(data):
    s = team_stats("Palmeiras", season=2022, data=data)
    assert s["team"] == "Palmeiras"
    assert s["season"] == 2022
    assert s["matches"] == s["wins"] + s["draws"] + s["losses"]
    assert s["matches"] > 0
    assert s["goals_for"] >= 0 and s["goals_against"] >= 0
    assert 0.0 <= s["win_rate"] <= 100.0


def test_team_stats_home_venue_filter(data):
    home = team_stats("Flamengo", season=2019, venue="home", data=data)
    away = team_stats("Flamengo", season=2019, venue="away", data=data)
    assert home["matches"] + away["matches"] == team_stats(
        "Flamengo", season=2019, data=data)["matches"]
    assert home["home_games"] == home["matches"]
    assert away["away_games"] == away["matches"]


def test_team_stats_by_competition(data):
    s = team_stats("Flamengo", competition="Copa do Brasil", data=data)
    assert s["matches"] > 0
    assert all(c for c in s["by_competition"])


def test_team_stats_unknown_team(data):
    s = team_stats("Definitely Not A Team 123", data=data)
    assert "error" in s


def test_compare_teams(data):
    c = compare_teams("Palmeiras", "Santos", season=2019, data=data)
    assert c["team_a"]["team"] == "Palmeiras"
    assert c["team_b"]["team"] == "Santos"
    assert "head_to_head" in c
    assert c["head_to_head"]["matches_played"] >= 0


def test_competitions_for_team(data):
    r = competitions_for_team("Flamengo", data=data)
    assert r["team"] == "Flamengo"
    comps = {c["competition"]: c["matches"] for c in r["competitions"]}
    assert "Brasileirão Serie A" in comps
    assert sum(comps.values()) > 0


def test_competitions_for_team_handles_name_variants(data):
    r1 = competitions_for_team("Flamengo", data=data)
    r2 = competitions_for_team("Flamengo-RJ", data=data)
    assert r1["team"] == r2["team"] == "Flamengo"
