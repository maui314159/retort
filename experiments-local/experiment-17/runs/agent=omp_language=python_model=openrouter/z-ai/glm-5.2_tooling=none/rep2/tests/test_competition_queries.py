"""BDD step definitions for competition-query scenarios."""

from __future__ import annotations

from pytest_bdd import scenarios, when, then, parsers

from brazilian_soccer import queries as Q

scenarios("features/competition_queries.feature")


@when(parsers.parse('I request the standings for "{competition}" in season {season:d}'))
def request_standings(data, ctx, competition, season):
    ctx["standings"] = Q.competition_standings(data, competition, season)


@when(parsers.parse('I request the champion of "{competition}" in season {season:d}'))
def request_champion(data, ctx, competition, season):
    ctx["champion"] = Q.competition_champion(data, competition, season)


@then("I should receive a sorted standings table")
def assert_sorted_table(ctx):
    table = ctx["standings"]
    assert len(table) > 0
    pts = [r["points"] for r in table]
    assert pts == sorted(pts, reverse=True), pts


@then(parsers.parse('the champion should be "{team}"'))
def assert_champion(ctx, team):
    if "standings" in ctx:
        assert ctx["standings"][0]["team"] == team, ctx["standings"][0]["team"]
    else:
        assert ctx["champion"] and team in ctx["champion"], ctx["champion"]


@then("the total points across teams should be positive")
def assert_total_points(ctx):
    total = sum(r["points"] for r in ctx["standings"])
    assert total > 0


@then("each team should have 38 played matches")
def assert_38_played(ctx):
    for r in ctx["standings"]:
        assert r["played"] == 38, r
