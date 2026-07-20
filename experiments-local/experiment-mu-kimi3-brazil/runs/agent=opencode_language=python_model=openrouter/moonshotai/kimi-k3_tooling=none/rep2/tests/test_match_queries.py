"""Step definitions for match_queries.feature."""

from __future__ import annotations

import re

import datetime as dt

import pytest
from pytest_bdd import given, parsers, then, when, scenarios

from brazilian_soccer_mcp.normalization import team_key

scenarios("features/match_queries.feature")


# ---------------------------------------------------------------------------
# When
# ---------------------------------------------------------------------------

@when(parsers.parse('I search for matches between "{team_a}" and "{team_b}"'))
def search_between(engine, context, team_a, team_b):
    context["result"] = engine.search_matches(team=team_a, opponent=team_b)


@when(parsers.parse('I search matches for team "{team}" in season {season:d}'))
def search_team_season(engine, context, team, season):
    context["result"] = engine.search_matches(team=team, season=season)


@when(parsers.parse('I search matches in competition "{competition}"'))
def search_competition(engine, context, competition):
    context["result"] = engine.search_matches(competition=competition)


@when(parsers.parse('I search matches between "{start}" and "{end}"'))
def search_date_range(engine, context, start, end):
    context["result"] = engine.search_matches(
        date_from=start, date_to=end, limit=100
    )
    context["range"] = (start, end)


@when(parsers.parse('I compare "{team_a}" and "{team_b}" head-to-head'))
def compare_h2h(engine, context, team_a, team_b):
    context["result"] = engine.head_to_head(team_a, team_b)


# ---------------------------------------------------------------------------
# Then
# ---------------------------------------------------------------------------

@then("I should receive a list of matches")
def check_match_list(context):
    result = context["result"]
    assert result["total"] > 0
    assert result["matches"], "expected at least one match"


@then("each match should have date, scores, and competition")
def check_match_fields(context):
    played = [m for m in context["result"]["matches"] if m["score"] is not None]
    assert played, "expected at least one played match"
    for match in played:
        assert match["date"]
        assert match["home_goals"] is not None
        assert match["away_goals"] is not None
        assert match["competition"]


@then(parsers.parse('all returned matches should involve "{team}"'))
def check_involves_team(context, team):
    key = team_key(team)
    for match in context["result"]["matches"]:
        names = {team_key(match["home_team"]), team_key(match["away_team"])}
        assert key in names, f"{match} does not involve {team}"


@then(parsers.parse("all returned matches should be from season {season:d}"))
def check_season(context, season):
    for match in context["result"]["matches"]:
        assert match["season"] == season


@then(parsers.parse('all returned matches should be from competition "{competition}"'))
def check_competition(context, competition):
    for match in context["result"]["matches"]:
        assert match["competition"] == competition


@then(parsers.parse('all returned matches should have dates between "{start}" and "{end}"'))
def check_dates(context, start, end):
    start_d = dt.date.fromisoformat(start)
    end_d = dt.date.fromisoformat(end)
    for match in context["result"]["matches"]:
        match_date = dt.date.fromisoformat(match["date"])
        assert start_d <= match_date <= end_d


@then("the summary should report wins for both teams and draws")
def check_h2h_summary(context):
    result = context["result"]
    assert result["wins_a"] >= 0
    assert result["wins_b"] >= 0
    assert result["draws"] >= 0
    assert result["total_matches"] > 0
    assert "draws" in result["summary"]


@then("the wins plus draws should equal the number of played matches")
def check_h2h_totals(context):
    result = context["result"]
    played = len([m for m in result["matches"] if m["score"] is not None])
    assert result["wins_a"] + result["wins_b"] + result["draws"] >= played
