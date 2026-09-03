"""BDD tests for statistical analysis queries.

Feature: Statistical Analysis

  Scenario: Average goals per match
    Given the match data is loaded
    When I request the average goals for the Brasileirão in 2019
    Then I should receive a per-match average and home/away win rates
    And the three rates should sum to roughly 100%

  Scenario: Biggest wins
    Given the match data is loaded
    When I request the biggest wins
    Then each result should have a positive goal difference and a date

  Scenario: Home vs away balance
    Given the match data is loaded
    When I request the home/away balance for 2019
    Then every team row should have home and away played/record fields

  Scenario: Derbies
    Given the match data is loaded
    When I request derbies for 2019
    Then each result should be a match between a traditional rival pair
"""

from __future__ import annotations

from brazilian_soccer_mcp.normalize import normalize_team_name
from brazilian_soccer_mcp.queries import (
    DERBY_PAIRS,
    average_goals,
    biggest_wins,
    derbies,
    home_away_balance,
)


def test_average_goals_2019(data):
    a = average_goals("Brasileirão Serie A", 2019, data=data)
    assert a["matches"] == 380
    assert 1.5 < a["average_goals_per_match"] < 3.5
    rate_sum = a["home_win_rate"] + a["away_win_rate"] + a["draw_rate"]
    assert abs(rate_sum - 100.0) < 1.0


def test_average_goals_all_competitions(data):
    a = average_goals(data=data)
    assert a["matches"] > 5_000
    assert a["average_goals_per_match"] > 0


def test_biggest_wins(data):
    rows = biggest_wins(limit=10, data=data)
    assert rows
    for r in rows:
        assert r["goal_difference"] > 0
        assert r["date"]
    diffs = [r["goal_difference"] for r in rows]
    assert diffs == sorted(diffs, reverse=True)


def test_home_away_balance_2019(data):
    bal = home_away_balance("Brasileirão Serie A", 2019, data=data)
    assert bal["teams"]
    for r in bal["teams"]:
        assert r["home_played"] == r["home_wins"] + r["home_draws"] + r["home_losses"]
        assert r["away_played"] == r["away_wins"] + r["away_draws"] + r["away_losses"]
        assert 0.0 <= r["home_win_rate"] <= 100.0


def test_derbies_2019(data):
    rows = derbies(season=2019, data=data)
    assert rows
    pairs = {frozenset((a, b)) for a, b in DERBY_PAIRS}
    for r in rows:
        pair = frozenset((normalize_team_name(r["home_team"]),
                          normalize_team_name(r["away_team"])))
        assert pair in pairs
        assert r["season"] == 2019


def test_derbies_all(data):
    rows = derbies(data=data)
    assert rows
