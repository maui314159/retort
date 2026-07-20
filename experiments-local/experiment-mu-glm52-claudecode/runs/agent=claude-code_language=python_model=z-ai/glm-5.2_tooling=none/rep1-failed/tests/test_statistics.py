"""BDD step definitions for the Statistical Analysis feature."""

from __future__ import annotations

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from brazilian_soccer_mcp import queries

scenarios("features/statistics.feature")


@given("the match data is loaded")
def match_data_loaded(kg):
    assert kg is not None and len(kg.dataset.matches) > 0


@when(
    'I request average goals for competition "{competition}"',
    target_fixture="result",
)
def request_avg_goals(kg, context, competition):
    res = queries.average_goals(kg, competition=competition)
    context["result"] = res
    return res


@when(
    'I request the biggest wins in competition "{competition}"',
    target_fixture="result",
)
def request_biggest_wins(kg, context, competition):
    res = queries.biggest_wins(kg, competition=competition, limit=10)
    context["result"] = res
    return res


@when(
    'I request home advantage for competition "{competition}" in season {season:d}',
    target_fixture="result",
)
def request_home_advantage(kg, context, competition, season):
    res = queries.home_advantage(kg, competition=competition, season=season)
    context["result"] = res
    return res


@when(
    'I request the best home record for competition "{competition}" in season {season:d}',
    target_fixture="result",
)
def request_best_home(kg, context, competition, season):
    res = queries.best_home_record(kg, competition=competition, season=season, limit=50)
    context["result"] = res
    return res


@when("I request the most active teams", target_fixture="result")
def request_most_active(kg, context):
    res = queries.biggest_team_dataset(kg, limit=10)
    context["result"] = res
    return res


@then("the average goals should be between 2 and 3")
def avg_goals_range(context):
    avg = context["result"]["average_goals"]
    assert 2.0 <= avg <= 3.0, f"average {avg} outside [2,3]"


@then("the home win rate should exceed the away win rate")
def home_gt_away(context):
    res = context["result"]
    assert res["home_win_rate"] > res["away_win_rate"]


@then("I should receive a list ranked by margin")
def biggest_wins_list(context):
    res = context["result"]
    assert "biggest_wins" in res
    rows = res["biggest_wins"]
    assert rows
    margins = [r["margin"] for r in rows]
    assert margins == sorted(margins, reverse=True)


@then("every margin should be positive")
def margins_positive(context):
    for r in context["result"]["biggest_wins"]:
        assert r["margin"] > 0


@then("I should receive a home advantage index")
def home_advantage_index(context):
    res = context["result"]
    assert "home_advantage_index" in res


@then("I should receive a ranked list of teams by home win rate")
def best_home_list(context):
    res = context["result"]
    assert "best_home_records" in res
    rows = res["best_home_records"]
    assert rows
    rates = [r["home_win_rate"] for r in rows]
    assert rates == sorted(rates, reverse=True)


@then("Flamengo should top the 2019 home record")
def flamengo_top_home(context):
    rows = context["result"]["best_home_records"]
    assert rows[0]["team"] == "Flamengo"


@then("I should receive a list of teams with match counts")
def most_active_list(context):
    res = context["result"]
    assert "most_active_teams" in res
    assert res["most_active_teams"]


@then("the list should be sorted by match count descending")
def most_active_sorted(context):
    counts = [r["matches"] for r in context["result"]["most_active_teams"]]
    assert counts == sorted(counts, reverse=True)
