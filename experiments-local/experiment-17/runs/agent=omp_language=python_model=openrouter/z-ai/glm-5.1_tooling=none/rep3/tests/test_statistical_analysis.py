"""
BDD step definitions for statistical_analysis.feature
"""

from __future__ import annotations

import json

from pytest_bdd import given, when, then, scenarios

scenarios("statistical_analysis.feature")


@given("the match data is loaded")
def match_data_loaded():
    pass


@when("I request average goals per match")
def avg_goals(invoker):
    invoker.result = json.loads(invoker.avg_goals_per_match())


@then("the result should include total matches and average goals")
def avg_goals_result(invoker):
    r = invoker.result
    assert "total_matches" in r
    assert "avg_goals_per_match" in r
    assert r["total_matches"] > 0
    assert r["avg_goals_per_match"] > 0


@when("I request the biggest wins")
def biggest_wins_req(invoker):
    invoker.result = json.loads(invoker.biggest_wins())


@then("I should receive results sorted by goal difference descending")
def biggest_wins_sorted(invoker):
    r = invoker.result
    assert isinstance(r, list)
    assert len(r) > 0
    diffs = [m["goal_difference"] for m in r]
    assert diffs == sorted(diffs, reverse=True)
    assert diffs[0] >= diffs[-1]


@when("I request home vs away statistics")
def home_away_req(invoker):
    invoker.result = json.loads(invoker.home_vs_away())


@then("I should receive home win rate and away win rate")
def home_away_result(invoker):
    r = invoker.result
    assert "home_win_rate" in r
    assert "away_win_rate" in r
    assert "avg_home_goals" in r
    assert "avg_away_goals" in r
    # Home advantage: home win rate should typically be higher
    assert r["home_win_rate"] > 0
