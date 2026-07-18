"""BDD step definitions for features/match_queries.feature.

Implements the scenarios described in TASK.md's testing approach using
pytest-bdd. Each scenario exercises a query capability end-to-end.
"""
from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from brazilian_soccer import queries as q
from brazilian_soccer.loader import load_matches, load_players

scenarios("features/match_queries.feature")


# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------

@pytest.fixture
def context():
    """A mutable dict shared across Given/When/Then steps within a scenario."""
    return {}


# ---------------------------------------------------------------------------
# Given
# ---------------------------------------------------------------------------

@given("the match data is loaded", target_fixture="context")
def match_data_loaded(context):
    df = load_matches()
    assert len(df) > 0
    context["matches_df"] = df
    return context


@given("the player data is loaded", target_fixture="context")
def player_data_loaded(context):
    df = load_players()
    assert len(df) > 0
    context["players_df"] = df
    return context


# ---------------------------------------------------------------------------
# When
# ---------------------------------------------------------------------------

@when(
    parsers.parse('I search for matches between "{team_a}" and "{team_b}"'),
    target_fixture="context",
)
def search_matches_between(context, team_a, team_b):
    context["result"] = q.find_matches(team=team_a, opponent=team_b, limit=200)
    return context


@when(
    parsers.parse('I request statistics for "{team}" in season {season:d}'),
    target_fixture="context",
)
def request_team_stats(context, team, season):
    context["result"] = q.team_statistics(team, season=season)
    return context


@when(
    parsers.parse('I search for "{team}" matches in "{competition}"'),
    target_fixture="context",
)
def search_by_competition(context, team, competition):
    context["result"] = q.find_matches(
        team=team, competition=competition, limit=200,
    )
    context["expected_competition"] = competition
    return context


@when(
    parsers.parse('I request head-to-head between "{team_a}" and "{team_b}"'),
    target_fixture="context",
)
def request_h2h(context, team_a, team_b):
    context["result"] = q.head_to_head(team_a, team_b, limit=500)
    return context


@when(
    parsers.parse('I request standings for "{competition}" season {season:d}'),
    target_fixture="context",
)
def request_standings(context, competition, season):
    context["result"] = q.competition_standings(competition, season)
    return context


@when(
    parsers.parse('I search for players named "{name}"'),
    target_fixture="context",
)
def search_players_by_name(context, name):
    context["result"] = q.search_players(name=name, limit=20)
    return context


@when(
    parsers.parse('I search for players from "{nationality}"'),
    target_fixture="context",
)
def search_players_by_nationality(context, nationality):
    context["result"] = q.search_players(nationality=nationality, limit=20)
    return context


# ---------------------------------------------------------------------------
# Then
# ---------------------------------------------------------------------------

@then("I should receive a list of matches")
def receive_match_list(context):
    assert isinstance(context["result"], list)
    assert len(context["result"]) > 0


@then("each match should have date, scores, and competition")
def match_has_fields(context):
    for m in context["result"]:
        assert "date" in m
        assert "home_goal" in m
        assert "away_goal" in m
        assert "competition" in m


@then("I should receive wins, losses, draws, and goals")
def receive_team_stats(context):
    rec = context["result"]
    assert "wins" in rec
    assert "losses" in rec
    assert "draws" in rec
    assert "goals_for" in rec
    assert "goals_against" in rec
    assert rec["played"] > 0


@then(parsers.parse('all returned matches should be from "{competition}"'))
def matches_from_competition(context, competition):
    for m in context["result"]:
        assert m["competition"] == competition


@then("I should receive win counts for both teams and draws")
def receive_h2h(context):
    h2h = context["result"]
    assert "team_a_wins" in h2h
    assert "team_b_wins" in h2h
    assert "draws" in h2h
    assert h2h["matches_found"] > 0


@then("I should receive a sorted table with points")
def receive_standings(context):
    standings = context["result"]
    assert len(standings) > 0
    pts = [s["points"] for s in standings]
    assert pts == sorted(pts, reverse=True)


@then("the first team should be the champion")
def first_is_champion(context):
    standings = context["result"]
    assert standings[0]["position"] == 1


@then("I should receive at least one player")
def receive_players(context):
    assert isinstance(context["result"], list)
    assert len(context["result"]) >= 1


@then("the player should have a rating")
def player_has_rating(context):
    for p in context["result"]:
        assert p["overall"] is not None


@then("all returned players should be Brazilian")
def players_are_brazilian(context):
    for p in context["result"]:
        assert p["nationality"] == "Brazil"


@then("each player should have an overall rating")
def players_have_overall(context):
    for p in context["result"]:
        assert p["overall"] is not None
