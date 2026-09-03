"""
Context block
=============
Brazilian Soccer MCP Server - BDD Step Definitions: Statistical Analysis
"""

from pytest_bdd import scenarios, given, when, then, parsers
import pytest

scenarios("features/statistical_queries.feature")


@pytest.fixture
def ctx():
    return {}


@given("the match data is loaded", target_fixture="match_data")
def match_data_loaded(engine):
    return engine


@when("I request the biggest wins in the Brasileirão", target_fixture="biggest")
def biggest_wins(match_data, ctx):
    ctx["biggest"] = match_data.biggest_wins(competition="brasileirao", limit=10)
    return ctx["biggest"]


@when("I request average goals for the Brasileirão in 2019", target_fixture="avg")
def avg_goals(match_data, ctx):
    ctx["avg"] = match_data.average_goals(competition="brasileirao", season=2019)
    return ctx["avg"]


@when("I request derbies in season 2023", target_fixture="derbies")
def derbies_2023(match_data, ctx):
    ctx["derbies"] = match_data.derbies(season=2023, limit=100)
    return ctx["derbies"]


@then("I should receive a list sorted by goal margin descending")
def assert_biggest(biggest):
    assert len(biggest) > 0
    margins = [b["margin"] for b in biggest]
    assert margins == sorted(margins, reverse=True)


@then("each result should name a winner, a loser and a score")
def assert_biggest_fields(biggest):
    for b in biggest:
        assert {"winner", "loser", "score", "margin"} <= set(b)


@then("the average goals per match should be a positive number")
def assert_avg_positive(avg):
    assert avg["average_goals_per_match"] > 0


@then("the home win rate, away win rate and draw rate should sum to 100")
def assert_rates(avg):
    total = avg["home_win_rate"] + avg["away_win_rate"] + avg["draw_rate"]
    assert abs(total - 100.0) < 0.01


@then("I should receive at least one derby")
def assert_derbies(derbies):
    assert len(derbies) >= 1


@then("every derby should be between traditional rivals")
def assert_derby_pairs(derbies):
    from brazilian_soccer_mcp.normalizer import is_derby
    for d in derbies:
        assert is_derby(d["home_team"], d["away_team"]), (d["home_team"], d["away_team"])
