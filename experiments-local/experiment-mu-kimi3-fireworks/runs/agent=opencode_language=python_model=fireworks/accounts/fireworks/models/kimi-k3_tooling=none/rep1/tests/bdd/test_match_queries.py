"""BDD step definitions for match_queries.feature."""

from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from soccer_mcp import queries as q

scenarios("../features/match_queries.feature")


@when(parsers.parse('I search for matches between "{team1}" and "{team2}"'))
def search_between(store, context, team1, team2):
    context["result"] = q.head_to_head(store, team1, team2)
    context["text"] = str(context["result"])


@when(parsers.parse('I search for matches of "{team}" in season {season:d}'))
def search_by_season(store, context, team, season):
    context["result"] = q.search_matches(store, team=team, season=season, limit=200)
    context["text"] = str(context["result"])


@when(parsers.parse('I search for matches of "{team}"'))
def search_by_team(store, context, team):
    try:
        context["result"] = q.search_matches(store, team=team, limit=200)
        context["error"] = None
    except q.QueryError as exc:
        context["result"] = None
        context["error"] = exc


@when(parsers.parse('I search for "{competition}" matches at stage "{stage}"'))
def search_by_stage(store, context, competition, stage):
    context["result"] = q.search_matches(store, competition=competition,
                                         stage=stage, limit=200)


@when(parsers.parse('I search for "{team}" matches between "{start}" and "{end}"'))
def search_by_dates(store, context, team, start, end):
    context["result"] = q.search_matches(store, team=team, date_from=start,
                                         date_to=end, limit=200)


@when(parsers.parse('I ask for the most recent match between "{team1}" and "{team2}"'))
def ask_last_match(store, context, team1, team2):
    m = q.last_match(store, team1, team2)
    context["result"] = {"matches": [m]}
    context["text"] = (
        f"{m['home_team']} {m['home_goals']}-{m['away_goals']} {m['away_team']}"
    )


@when(parsers.parse("I search for derby matches in season {season:d}"))
def search_derbies(store, context, season):
    context["result"] = q.find_derbies(store, season=season, limit=200)


@then("I should receive a list of matches")
def receive_matches(context):
    assert context["result"] is not None
    assert context["result"]["matches"], "expected at least one match"


@then("each match should have date, scores, and competition")
def matches_have_details(context):
    for m in context["result"]["matches"]:
        assert m["date"], f"missing date: {m}"
        assert m["home_goals"] is not None and m["away_goals"] is not None
        assert m["competition"]


@then(parsers.parse('every match should involve "{team}"'))
def matches_involve_team(context, team):
    for m in context["result"]["matches"]:
        assert team in (m["home_team"], m["away_team"])


@then(parsers.parse("I should receive at least {count:d} matches"))
def receive_at_least(context, count):
    assert context["result"]["total"] >= count


@then(parsers.parse('every match should be a "{stage}"'))
def matches_are_stage(context, stage):
    for m in context["result"]["matches"]:
        assert m["stage"] == stage


@then(parsers.parse('every match should be in "{competition}"'))
def matches_in_competition(context, competition):
    for m in context["result"]["matches"]:
        assert m["competition"] == competition


@then("every match date should be within the range")
def dates_within_range(context):
    for m in context["result"]["matches"]:
        assert "2019-01-01" <= m["date"] <= "2019-06-30"


@then("the result should mention a score")
def result_mentions_score(context):
    assert "-" in context["text"]
    digits = [ch for ch in context["text"] if ch.isdigit()]
    assert digits


@then("every match should be a named derby")
def matches_are_derbies(context):
    for m in context["result"]["matches"]:
        assert m["derby"]


@then(parsers.parse('the search should find as many matches as searching for "{other}"'))
def same_match_count(store, context, other):
    baseline = q.search_matches(store, team=other, season=2022)
    assert context["result"]["total"] == baseline["total"] > 0


@then("the search should report an unknown team")
def unknown_team_reported(context):
    assert context["error"] is not None
    assert "Unknown team" in str(context["error"])
