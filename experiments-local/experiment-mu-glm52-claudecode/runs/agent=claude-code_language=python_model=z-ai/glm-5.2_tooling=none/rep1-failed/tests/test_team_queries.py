"""BDD step definitions for the Team Queries feature."""

from __future__ import annotations

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from brazilian_soccer_mcp import queries

scenarios("features/team_queries.feature")


@given("the match data is loaded")
def match_data_loaded(kg):
    assert kg is not None and len(kg.dataset.matches) > 0


@when(
    'I request statistics for "{team}" in season {season:d}',
    target_fixture="result",
)
def request_team_stats(kg, context, team, season):
    res = queries.team_stats(kg, team, season=season)
    context["result"] = res
    return res


@when(
    'I request home statistics for "{team}" in season {season:d}',
    target_fixture="result",
)
def request_team_home_stats(kg, context, team, season):
    res = queries.team_stats(kg, team, season=season, venue="home")
    context["result"] = res
    return res


@when(
    'I request the head-to-head between "{team_a}" and "{team_b}"',
    target_fixture="result",
)
def request_h2h(kg, context, team_a, team_b):
    res = queries.head_to_head(kg, team_a, team_b)
    context["result"] = res
    return res


@when('I request info for "{team}"', target_fixture="result")
def request_team_info(kg, context, team):
    res = queries.team_info(kg, team)
    context["result"] = res
    return res


@then("I should receive wins, losses, draws and goals")
def team_stats_fields(context):
    res = context["result"]
    for key in ("wins", "draws", "losses", "goals_for", "goals_against"):
        assert key in res, f"missing {key}"


@then("the matches count should equal wins plus draws plus losses")
def matches_equals_wdl(context):
    res = context["result"]
    assert res["matches"] == res["wins"] + res["draws"] + res["losses"]


@then("I should receive a home wins, draws and losses breakdown")
def home_breakdown(context):
    res = context["result"]
    assert "home" in res
    for key in ("wins", "draws", "losses"):
        assert key in res["home"]


@then("every counted match should be a home match")
def home_only(context, kg):
    # Cross-check: home wins+draws+losses should equal total matches for a
    # home-only query, since every returned match is a home game.
    res = context["result"]
    home = res["home"]
    assert res["matches"] == home["wins"] + home["draws"] + home["losses"]


@then("I should receive totals for both teams")
def h2h_totals(context):
    res = context["result"]
    for key in ("team_a_wins", "team_b_wins", "draws"):
        assert key in res


@then("both team win counts should be non-negative integers")
def h2h_nonneg(context):
    res = context["result"]
    assert isinstance(res["team_a_wins"], int) and res["team_a_wins"] >= 0
    assert isinstance(res["team_b_wins"], int) and res["team_b_wins"] >= 0


@then("I should receive a competitions map and an overall record")
def team_info_fields(context):
    res = context["result"]
    assert "competitions" in res and isinstance(res["competitions"], dict)
    assert "overall_record" in res


@then("the team name should be the canonical form")
def team_info_canonical(context):
    res = context["result"]
    assert res["team"] == "Flamengo"
