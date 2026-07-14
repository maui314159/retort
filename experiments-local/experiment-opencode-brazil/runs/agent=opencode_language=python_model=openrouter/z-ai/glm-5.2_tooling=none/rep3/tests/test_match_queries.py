"""BDD step definitions for Match Queries feature.

Context block
-------------
Implements Given/When/Then steps for ``match_queries.feature`` using the
query functions in ``brazilian_soccer_mcp.queries``.
"""
from __future__ import annotations

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from brazilian_soccer_mcp.data_loader import normalize_team_name

scenarios("features/match_queries.feature")


@given("the match data is loaded", target_fixture="match_ctx")
def match_data_loaded(loader):
    assert not loader.matches.empty, "Match data failed to load"
    return {"loader": loader, "result": None}


# ---- When steps -----------------------------------------------------------

@when(parsers.parse('I search for matches between "{team_a}" and "{team_b}"'),
      target_fixture="match_ctx")
def search_between(match_ctx, queries, team_a, team_b):
    match_ctx["result"] = queries["find_matches"](
        match_ctx["loader"], team=team_a, opponent=team_b
    )
    return match_ctx


@when(parsers.parse('I search for matches with team "{team}" in season {season:d}'),
      target_fixture="match_ctx")
def search_team_season(match_ctx, queries, team, season):
    match_ctx["result"] = queries["find_matches"](
        match_ctx["loader"], team=team, season=season
    )
    return match_ctx


@when(parsers.parse('I search for matches in competition "{competition}"'),
      target_fixture="match_ctx")
def search_competition(match_ctx, queries, competition):
    match_ctx["result"] = queries["find_matches"](
        match_ctx["loader"], competition=competition
    )
    return match_ctx


@when(parsers.parse('I request the last match between "{team_a}" and "{team_b}"'),
      target_fixture="match_ctx")
def last_match(match_ctx, queries, team_a, team_b):
    match_ctx["result"] = queries["last_match_between"](
        match_ctx["loader"], team_a, team_b
    )
    return match_ctx


@when(parsers.parse('I request the head-to-head record for "{team_a}" vs "{team_b}"'),
      target_fixture="match_ctx")
def h2h(match_ctx, queries, team_a, team_b):
    match_ctx["result"] = queries["find_head_to_head"](
        match_ctx["loader"], team_a, team_b
    )
    return match_ctx


# ---- Then steps -----------------------------------------------------------

@then("I should receive a list of matches")
def should_receive_list(match_ctx):
    assert isinstance(match_ctx["result"], list)
    assert len(match_ctx["result"]) > 0


@then("each match should have a date, scores, and competition")
def each_match_has_fields(match_ctx):
    for m in match_ctx["result"]:
        assert "date" in m
        assert "home_goal" in m
        assert "away_goal" in m
        assert "competition" in m


@then("every match should involve Palmeiras in 2023")
def every_match_palmeiras_2023(match_ctx):
    target = normalize_team_name("Palmeiras")
    for m in match_ctx["result"]:
        teams = {normalize_team_name(m["home_team"]), normalize_team_name(m["away_team"])}
        assert target in teams
        assert m["season"] == 2023


@then("every match should belong to the Libertadores competition")
def every_match_libertadores(match_ctx):
    for m in match_ctx["result"]:
        assert "libertadores" in m["competition"].lower()


@then("I should receive a single match")
def should_receive_single(match_ctx):
    assert match_ctx["result"] is not None
    assert isinstance(match_ctx["result"], dict)


@then("the match should have a valid date")
def match_has_valid_date(match_ctx):
    assert match_ctx["result"]["date"] is not None


@then("I should receive wins, draws, losses, and goals")
def h2h_fields(match_ctx):
    r = match_ctx["result"]
    for key in ("team_a_wins", "team_b_wins", "draws", "team_a_goals", "team_b_goals"):
        assert key in r


@then("the total matches played should equal the sum of results")
def h2h_total(match_ctx):
    r = match_ctx["result"]
    assert r["matches_played"] == r["team_a_wins"] + r["team_b_wins"] + r["draws"]
