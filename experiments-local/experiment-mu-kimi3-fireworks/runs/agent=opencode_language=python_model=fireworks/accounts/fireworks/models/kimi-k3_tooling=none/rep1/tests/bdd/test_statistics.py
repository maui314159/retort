"""BDD step definitions for statistics.feature."""

from __future__ import annotations

from pytest_bdd import parsers, scenarios, then, when

from soccer_mcp import queries as q

scenarios("../features/statistics.feature")


@when(parsers.parse('I ask for statistics of the "{competition}"'))
def comp_stats(store, context, competition):
    context["result"] = q.competition_stats(store, competition)


@when(parsers.parse("I ask for the {limit:d} biggest victories"))
def biggest(store, context, limit):
    context["result"] = q.biggest_wins(store, limit=limit)


@when(parsers.parse('I ask for the best away records of "{competition}" season {season:d}'))
def best_away(store, context, competition, season):
    context["result"] = q.best_away_records(store, competition, season)


@when(parsers.parse('I compare "{competition}" seasons {a:d} and {b:d}'))
def compare(store, context, competition, a, b):
    context["result"] = q.season_comparison(store, competition, a, b)


@then(parsers.parse("the average goals per match should be between {low:f} and {high:f}"))
def avg_goals_between(context, low, high):
    assert low < context["result"]["avg_goals_per_match"] < high


@then(parsers.parse("the home win rate should be between {low:d} and {high:d} percent"))
def home_rate_between(context, low, high):
    assert low < context["result"]["home_win_rate"] < high


@then("home, draw and away rates should sum to 100 percent")
def rates_sum(context):
    stats = context["result"]
    total = stats["home_win_rate"] + stats["draw_rate"] + stats["away_win_rate"]
    assert abs(total - 100.0) < 0.3


@then("the margins should be sorted descending")
def margins_sorted(context):
    margins = [m["margin"] for m in context["result"]["matches"]]
    assert margins == sorted(margins, reverse=True)


@then(parsers.parse("the biggest margin should be at least {margin:d} goals"))
def biggest_margin(context, margin):
    assert context["result"]["matches"][0]["margin"] >= margin


@then("the teams should be ranked by win rate")
def ranked_by_win_rate(context):
    rates = [t["win_rate"] for t in context["result"]["teams"]]
    assert rates == sorted(rates, reverse=True)
    assert context["result"]["teams"]


@then(parsers.parse("both seasons should report {matches:d} matches"))
def both_seasons_matches(context, matches):
    assert context["result"]["season_a"]["matches"] == matches
    assert context["result"]["season_b"]["matches"] == matches


@then("the comparison should include average goals and home win rate")
def comparison_fields(context):
    assert "avg_goals_per_match" in context["result"]["season_a"]
    assert "home_win_rate" in context["result"]["season_b"]
    assert "avg_goals_delta" in context["result"]
