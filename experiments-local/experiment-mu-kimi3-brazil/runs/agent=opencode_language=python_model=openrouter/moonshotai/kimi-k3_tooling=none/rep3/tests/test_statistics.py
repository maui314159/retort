"""Step definitions for statistics.feature."""

from __future__ import annotations

import time

from pytest_bdd import parsers, scenarios, then, when

import query_engine as qe

scenarios("features/statistics.feature")


@when(parsers.parse('I request the overview of competition "{comp}"'))
def overview(store, context, comp):
    context["result"] = qe.competition_overview(competition=comp, store=store)


@when(parsers.parse('I request the overview of competition "{comp}" for '
                    'season {season:d}'))
def overview_season(store, context, comp, season):
    result = qe.competition_overview(competition=comp, season=season,
                                     store=store)
    context.setdefault("results", []).append(result)
    context["result"] = result


@when(parsers.parse("I request the {limit:d} biggest wins"))
def biggest(store, context, limit):
    context["result"] = qe.biggest_wins(limit=limit, store=store)


@when(parsers.parse('I request the best home records of competition "{comp}" '
                    'for season {season:d}'))
def best_home(store, context, comp, season):
    context["result"] = qe.best_team_records(competition=comp, season=season,
                                             venue="home", store=store)


@when(parsers.parse('I time a head-to-head lookup between "{team1}" and '
                    '"{team2}"'))
def timed_lookup(store, context, team1, team2):
    start = time.perf_counter()
    context["result"] = qe.head_to_head(team1, team2, store=store)
    context["elapsed"] = time.perf_counter() - start


@when(parsers.parse("I time a standings request for season {season:d}"))
def timed_aggregate(store, context, season):
    start = time.perf_counter()
    context["result"] = qe.competition_standings(season=season, store=store)
    context["elapsed"] = time.perf_counter() - start


@then(parsers.parse("the average goals per match should be between "
                    "{low:g} and {high:g}"))
def check_avg_goals(context, low, high):
    assert low <= context["result"]["avg_goals_per_match"] <= high


@then("the home, draw and away rates should add up to 100 percent")
def check_rates(context):
    result = context["result"]
    total = (result["home_win_rate_pct"] + result["draw_rate_pct"]
             + result["away_win_rate_pct"])
    assert abs(total - 100.0) < 0.2


@then(parsers.parse("both seasons should have {matches:d} matches"))
def check_both_seasons(context, matches):
    assert len(context["results"]) == 2
    for result in context["results"]:
        assert result["matches"] == matches


@then(parsers.parse("the biggest win should have a margin of at least "
                    "{margin:d} goals"))
def check_biggest_margin(context, margin):
    assert context["result"]["matches"][0]["margin"] >= margin


@then("the margins should be sorted in descending order")
def check_margins_sorted(context):
    margins = [m["margin"] for m in context["result"]["matches"]]
    assert margins == sorted(margins, reverse=True)


@then(parsers.parse("every listed team should have at least {count:d} home "
                    "matches"))
def check_min_home_matches(context, count):
    assert len(context["result"]["teams"]) > 0
    for row in context["result"]["teams"]:
        assert row["matches"] >= count


@then("the teams should be sorted by descending points per game")
def check_ppg_sorted(context):
    ppgs = [row["points_per_game"] for row in context["result"]["teams"]]
    assert ppgs == sorted(ppgs, reverse=True)


@then(parsers.parse("the lookup should take less than {seconds:d} seconds"))
def check_lookup_time(context, seconds):
    assert context["elapsed"] < seconds
    assert context["result"]["total_matches"] > 0


@then(parsers.parse("the aggregate query should take less than {seconds:d} "
                    "seconds"))
def check_aggregate_time(context, seconds):
    assert context["elapsed"] < seconds
    assert context["result"]["total_teams"] > 0
