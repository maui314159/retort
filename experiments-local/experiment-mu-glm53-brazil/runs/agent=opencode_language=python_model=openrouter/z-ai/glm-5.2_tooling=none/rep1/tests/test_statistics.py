"""
BDD (Given/When/Then) scenarios for statistical analysis queries.

Context block
=============
Purpose: validate the statistical-analysis capability (TASK.md section
"Statistical Analysis"): average goals, home/away win rates, biggest
victories, best away record and top-scoring teams.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Feature: Statistical Analysis
# ---------------------------------------------------------------------------


def test_average_goals_per_match(engine):
    """Scenario: Average goals in the Brasileirao.

    Given the match data is loaded
    When I request the average goals for the Brasileirao
    Then I should receive a positive average and home/draw/away win rates
    And the three rates should sum to 1.0
    """
    stats = engine.average_goals(competition="Brasileirao")
    assert stats["matches"] > 0
    assert stats["avg_goals"] > 0
    total = stats["home_win_rate"] + stats["draw_rate"] + stats["away_win_rate"]
    assert abs(total - 1.0) < 1e-3


def test_biggest_wins_sorted_by_goal_difference(engine):
    """Scenario: Biggest victories in the dataset.

    Given the match data is loaded
    When I request the biggest wins
    Then results should be sorted by goal difference descending
    And every result should be a decisive victory (no draws)
    """
    wins = engine.biggest_wins(limit=10)
    assert len(wins) > 0
    diffs = [w["goal_difference"] for w in wins]
    assert diffs == sorted(diffs, reverse=True)
    for w in wins:
        assert w["home_goal"] != w["away_goal"]
        assert w["goal_difference"] == abs(w["home_goal"] - w["away_goal"])


def test_best_away_record_ranked(engine):
    """Scenario: Best away record.

    Given the match data is loaded
    When I request the best away records for the Brasileirao
    Then each team should have at least 5 away games
    And results should be sorted by win rate descending
    """
    rows = engine.best_away_record(competition="Brasileirao", limit=10)
    assert len(rows) > 0
    for r in rows:
        assert r["played"] >= 5
    rates = [r["win_rate"] for r in rows]
    assert rates == sorted(rates, reverse=True)


def test_top_scoring_teams_ranked(engine):
    """Scenario: Top scoring teams.

    Given the match data is loaded
    When I request the top scoring teams in 2019 Brasileirao
    Then results should be sorted by goals descending
    """
    rows = engine.top_scoring_teams(competition="Brasileirao", season="2019", limit=10)
    assert len(rows) > 0
    goals = [r["goals"] for r in rows]
    assert goals == sorted(goals, reverse=True)


def test_home_advantage_exists(engine):
    """Scenario: Home advantage is observable.

    Given the match data is loaded
    When I compute the home vs away win rates across all Brasileirao matches
    Then the home win rate should exceed the away win rate
    """
    stats = engine.average_goals(competition="Brasileirao")
    assert stats["home_win_rate"] > stats["away_win_rate"]
