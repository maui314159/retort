"""BDD step definitions for match-query scenarios."""

from __future__ import annotations

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from brazilian_soccer import queries as Q

scenarios("features/match_queries.feature")


@when('I search for matches between "Flamengo" and "Fluminense"')
def search_between_two(data, ctx):
    ctx["matches"] = Q.search_matches(data, team="Flamengo",
                                       opponent="Fluminense", limit=0)


@when(parsers.parse('I search for matches of team "{team}" in season {season:d}'))
def search_team_season(data, ctx, team, season):
    ctx["matches"] = Q.search_matches(data, team=team, season=season, limit=0)


@when(parsers.parse('I search for matches in competition "{competition}" in season {season:d}'))
def search_competition_season(data, ctx, competition, season):
    ctx["matches"] = Q.search_matches(data, competition=competition,
                                       season=season, limit=0)


@when(parsers.parse('I request the last match between "{a}" and "{b}"'))
def last_match(data, ctx, a, b):
    ctx["match"] = Q.last_match(data, a, b)


@when(parsers.parse('I request statistics for "{team}" in season {season:d} and competition "{competition}"'))
def stats_filtered(data, ctx, team, season, competition):
    ctx["stats"] = Q.team_stats(data, team, season=season, competition=competition)


@then("I should receive a list of matches")
def assert_list(ctx):
    assert isinstance(ctx["matches"], list)
    assert len(ctx["matches"]) > 0


@then("each match should have date, scores, and competition")
def assert_match_fields(ctx):
    required = {"date", "competition", "home", "away", "home_goals",
                "away_goals"}
    for m in ctx["matches"]:
        assert required.issubset(m.keys()), m
        assert m["competition"]


@then(parsers.parse('every match should involve either "{a}" or "{b}"'))
def assert_involves_either(data, ctx, a, b):
    ka, kb = data.resolve_team(a), data.resolve_team(b)
    for m in ctx["matches"]:
        # The match dict carries display names; resolve via team_name lookup
        # by checking the home/away display against the two teams.
        names = {m["home"], m["away"]}
        expected = {data.team_name(ka), data.team_name(kb)}
        assert names & expected, (m, expected)


@then(parsers.parse('every match should be in season {season:d}'))
def assert_season(ctx, season):
    for m in ctx["matches"]:
        assert m["season"] == season, m


@then(parsers.parse('every match should involve "{team}"'))
def assert_involves(data, ctx, team):
    expected = data.team_name(data.resolve_team(team))
    for m in ctx["matches"]:
        assert expected in (m["home"], m["away"]), (m, expected)


@then(parsers.parse('every match should have competition "{competition}"'))
def assert_competition(ctx, competition):
    from brazilian_soccer.normalize import canonical_competition
    canon = canonical_competition(competition)
    for m in ctx["matches"]:
        assert m["competition"] == canon, m


@then("I should receive a single match")
def assert_single(ctx):
    assert ctx["match"] is not None
    assert "home" in ctx["match"]


@then("the match should have a date and scores")
def assert_match_has_scores(ctx):
    m = ctx["match"]
    assert m["date"] is not None
    assert m["home_goals"] is not None and m["away_goals"] is not None


@then(parsers.parse("the matches played should be at most {n:d}"))
def assert_at_most(ctx, n):
    assert ctx["stats"]["matches"] <= n, ctx["stats"]
