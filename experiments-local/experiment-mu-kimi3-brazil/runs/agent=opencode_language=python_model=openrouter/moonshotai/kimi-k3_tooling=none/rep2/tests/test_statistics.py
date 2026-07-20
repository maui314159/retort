"""Step definitions for statistics.feature."""

from __future__ import annotations

import time

from pytest_bdd import parsers, then, when, scenarios

scenarios("features/statistics.feature")


# ---------------------------------------------------------------------------
# When
# ---------------------------------------------------------------------------

@when(parsers.parse("I request the {limit:d} biggest wins"))
def request_biggest_wins(engine, context, limit):
    context["result"] = engine.biggest_wins(limit=limit)


@when(parsers.parse('I request aggregate stats for competition "{competition}"'))
def request_comp_stats(engine, context, competition):
    context["result"] = engine.competition_stats(competition=competition)


@when(parsers.parse('I request aggregate stats for competition "{competition}" season {season:d}'))
def request_comp_season_stats(engine, context, competition, season):
    context["result"] = engine.competition_stats(competition=competition, season=season)


@when(parsers.parse('I search players at club "{club}" and matches for team "{team}"'))
def cross_file_query(engine, context, club, team):
    context["players"] = engine.search_players(club=club)
    context["matches"] = engine.search_matches(team=team)


# ---------------------------------------------------------------------------
# Then
# ---------------------------------------------------------------------------

@then(parsers.parse("I should receive exactly {count:d} matches"))
def check_match_count(context, count):
    assert len(context["result"]["biggest_wins"]) == count


@then("the victory margins should be sorted descending")
def check_margins_sorted(context):
    margins = [m["margin"] for m in context["result"]["biggest_wins"]]
    assert margins == sorted(margins, reverse=True)
    assert margins[0] >= 5, "expected a truly big win at the top"


@then(parsers.parse("the average goals per match should be greater than {minimum:g}"))
def check_avg_goals(context, minimum):
    assert context["result"]["avg_goals_per_match"] > minimum


@then("home, draw and away rates should sum to 100 percent")
def check_rates_sum(context):
    result = context["result"]
    total = result["home_win_rate"] + result["draw_rate"] + result["away_win_rate"]
    assert abs(total - 100.0) < 0.2


@then(parsers.parse("the match count should be {count:d}"))
def check_stats_match_count(context, count):
    assert context["result"]["matches"] == count


@then("both queries should return results")
def check_cross_file(context):
    assert context["players"]["total"] > 0
    assert context["matches"]["total"] > 0


@then("a simple lookup should respond in under 2 seconds")
def check_lookup_performance(engine):
    start = time.perf_counter()
    engine.search_matches(team="Flamengo", opponent="Corinthians", limit=5)
    engine.search_players(name="Neymar")
    assert time.perf_counter() - start < 2.0


@then("an aggregate query should respond in under 5 seconds")
def check_aggregate_performance(engine):
    start = time.perf_counter()
    engine.standings(2019)
    engine.competition_stats(competition="Brasileirão")
    engine.biggest_wins(limit=10)
    assert time.perf_counter() - start < 5.0
