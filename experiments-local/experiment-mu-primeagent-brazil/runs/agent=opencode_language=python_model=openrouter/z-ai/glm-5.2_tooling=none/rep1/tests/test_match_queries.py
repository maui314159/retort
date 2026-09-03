"""BDD tests for match queries.

Feature: Match Queries

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores and competition

  Scenario: Get head-to-head record between two teams
    Given the match data is loaded
    When I request the head-to-head between "Flamengo" and "Fluminense"
    Then I should receive wins, losses and draws for both teams
    And the match counts should reconcile

  Scenario: Filter matches by competition and season
    Given the match data is loaded
    When I search for Libertadores matches in 2019
    Then every result should be from the Copa Libertadores in 2019
"""

from __future__ import annotations

from brazilian_soccer_mcp.queries import (
    find_matches,
    head_to_head,
)


def test_find_matches_between_two_teams(data):
    rows = find_matches("Flamengo", "Fluminense", limit=10_000, data=data)
    assert rows, "expected some Flamengo vs Fluminense matches"
    teams = {"Flamengo", "Fluminense"}
    for r in rows:
        assert {r["home_team"], r["away_team"]} == teams
        assert r["date"] is not None
        assert isinstance(r["home_goal"], int) and isinstance(r["away_goal"], int)
        assert r["competition"]


def test_find_matches_by_single_team(data):
    rows = find_matches("Palmeiras", limit=20, data=data)
    assert len(rows) == 20
    assert all("Palmeiras" in (r["home_team"], r["away_team"]) for r in rows)


def test_find_matches_filtered_by_competition_and_season(data):
    rows = find_matches(competition="Libertadores", season=2019, limit=100_000, data=data)
    assert rows
    assert all(r["competition"] == "Copa Libertadores" for r in rows)
    assert all(r["season"] == 2019 for r in rows)


def test_find_matches_date_range(data):
    rows = find_matches(
        team="Flamengo", start_date="2019-01-01", end_date="2019-12-31",
        limit=100_000, data=data,
    )
    assert rows
    assert all(r["date"] and r["date"].startswith("2019") for r in rows)


def test_head_to_head_record(data):
    h = head_to_head("Flamengo", "Fluminense", data=data)
    assert h["team_a"] == "Flamengo"
    assert h["team_b"] == "Fluminense"
    assert h["matches_played"] == h["team_a_wins"] + h["team_b_wins"] + h["draws"]
    assert h["matches_played"] > 0
    assert len(h["matches"]) == h["matches_played"]


def test_head_to_head_unknown_team_returns_error(data):
    h = head_to_head("Flamengo", "Some Nonexistent Team XYZ", data=data)
    assert "error" in h


def test_find_matches_returns_empty_for_unknown_team(data):
    rows = find_matches("Definitely Not A Team 123", limit=10, data=data)
    assert rows == []
