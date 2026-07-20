"""BDD step definitions for the Match Queries feature.

Context
-------
Implements the Given/When/Then steps from
``tests/features/match_queries.feature``.  Step functions mutate the
``context`` fixture (set ``context["result"]`` to the query output) so
the "Then" steps can assert on it without re-running the query.

The "When" steps delegate to the pure query layer
(:mod:`brazilian_soccer_mcp.queries`) — exercising the MCP tool layer's
exact downstream code path without paying the FastMCP transport cost on
every scenario.
"""

from __future__ import annotations

from datetime import date

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from brazilian_soccer_mcp import queries

scenarios("features/match_queries.feature")


@given("the match data is loaded", target_fixture="kg_loaded")
def match_data_loaded(kg):
    """The session knowledge graph fixture is already loaded; assert it."""

    assert kg is not None and len(kg.dataset.matches) > 0
    return kg


@when(
    'I search for matches between "{team_a}" and "{team_b}"',
    target_fixture="result",
)
def search_matches_between_teams(kg, context, team_a, team_b):
    res = queries.find_matches(kg, team=team_a, opponent=team_b, limit=200)
    context["result"] = res
    return res


@when(
    'I search for matches of team "{team}" in season {season:d}',
    target_fixture="result",
)
def search_matches_team_season(kg, context, team, season):
    res = queries.find_matches(kg, team=team, season=season, limit=200)
    context["result"] = res
    return res


@when(
    'I search for matches in competition "{competition}" in season {season:d}',
    target_fixture="result",
)
def search_matches_competition_season(kg, context, competition, season):
    res = queries.find_matches(kg, competition=competition, season=season, limit=200)
    context["result"] = res
    return res


@when(
    'I search for matches between "{start}" and "{end}"',
    target_fixture="result",
)
def search_matches_date_range(kg, context, start, end):
    res = queries.find_matches(
        kg,
        start_date=date.fromisoformat(start),
        end_date=date.fromisoformat(end),
        limit=200,
    )
    context["result"] = res
    return res


@when(
    'I request the head-to-head record between "{team_a}" and "{team_b}"',
    target_fixture="result",
)
def head_to_head(kg, context, team_a, team_b):
    res = queries.head_to_head(kg, team_a, team_b)
    context["result"] = res
    return res


# ---------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------


@then("I should receive a list of matches")
def should_receive_list(context):
    res = context["result"]
    assert isinstance(res, dict)
    assert res.get("total", 0) >= 1, "expected at least one match"
    assert isinstance(res.get("matches"), list)


@then("each match should have a date, scores and competition")
def each_match_has_fields(context):
    for m in context["result"]["matches"]:
        assert "date" in m
        assert "score" in m and "home" in m["score"] and "away" in m["score"]
        assert "competition" in m


@then('Flamengo and Fluminense should both appear in every match')
def both_teams_appear(context):
    for m in context["result"]["matches"]:
        teams = {m["home_team"], m["away_team"]}
        assert "Flamengo" in teams
        assert "Fluminense" in teams


@then("every match should involve Palmeiras")
def every_match_involves_palmeiras(context):
    for m in context["result"]["matches"]:
        teams = {m["home_team"], m["away_team"]}
        assert "Palmeiras" in teams


@then("every match should have season {season:d}")
def every_match_has_season(context, season):
    for m in context["result"]["matches"]:
        assert m["season"] == season


@then('every match should belong to competition "{competition}"')
def every_match_competition(context, competition):
    for m in context["result"]["matches"]:
        assert m["competition"] == competition


@then("every match date should fall within September 2019")
def every_match_within_sept_2019(context):
    for m in context["result"]["matches"]:
        d = date.fromisoformat(m["date"])
        assert d.year == 2019 and d.month == 9


@then("I should receive a summary with total matches, wins, draws and goals")
def head_to_head_summary(context):
    res = context["result"]
    for key in ("total_matches", "team_a_wins", "team_b_wins", "draws",
                "team_a_goals", "team_b_goals"):
        assert key in res


@then("the wins plus draws plus losses should equal the total matches")
def h2h_wins_draws_losses_total(context):
    res = context["result"]
    total = res["total_matches"]
    assert res["team_a_wins"] + res["team_b_wins"] + res["draws"] == total
