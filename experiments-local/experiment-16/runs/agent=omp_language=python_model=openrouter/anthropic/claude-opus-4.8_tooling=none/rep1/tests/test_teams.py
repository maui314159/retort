"""
================================================================================
Context
--------------------------------------------------------------------------------
Module  : tests.test_teams
Purpose : BDD steps for features/teams.feature - team W/D/L and goal records,
          venue filtering and exclusion of scoreless fixtures.
================================================================================
"""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/teams.feature")


@given("the soccer knowledge graph is loaded", target_fixture="graph")
def _loaded(sample_graph):
    return sample_graph


@when(parsers.parse('I request the team record for "{team}" in season {season:d}'))
def _record(graph, ctx, team, season):
    ctx["record"] = graph.team_record(team, season=season)
    ctx["all_record"] = ctx["record"]


@when(parsers.parse('I request the home record for "{team}" in season {season:d}'))
def _home(graph, ctx, team, season):
    ctx["home_record"] = graph.team_record(team, season=season, venue="home")
    ctx["all_record"] = graph.team_record(team, season=season)


@then("I should receive wins, losses, draws and goals")
def _fields(ctx):
    r = ctx["record"]
    for attr in ("wins", "losses", "draws", "goals_for", "goals_against"):
        assert getattr(r, attr) >= 0


@then("the totals should be internally consistent")
def _consistent(ctx):
    r = ctx["record"]
    assert r.wins + r.draws + r.losses == r.matches
    assert r.points == r.wins * 3 + r.draws


@then("the home matches should be fewer than or equal to all matches")
def _home_le(ctx):
    assert ctx["home_record"].matches <= ctx["all_record"].matches


@then("the counted matches should exclude the scoreless fixture")
def _exclude(graph, ctx):
    # Flamengo 2023 has 7 scored matches + 1 postponed (no score) in the sample.
    listed = graph.find_matches(team="Flamengo", season=2023)
    scored = [m for m in listed if m.has_score]
    assert len(listed) > len(scored)
    assert ctx["all_record"].matches == len(scored)
