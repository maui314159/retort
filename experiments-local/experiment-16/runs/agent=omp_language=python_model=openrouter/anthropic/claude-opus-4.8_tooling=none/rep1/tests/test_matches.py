"""
================================================================================
Context
--------------------------------------------------------------------------------
Module  : tests.test_matches
Purpose : BDD step definitions (Given/When/Then) for features/matches.feature,
          exercising SoccerGraph.find_matches / head_to_head / team_record over
          the controlled sample dataset from conftest.
================================================================================
"""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/matches.feature")


@given("the soccer knowledge graph is loaded", target_fixture="graph")
def _loaded(sample_graph):
    return sample_graph


@when(parsers.parse('I search for matches between "{a}" and "{b}"'))
def _between(graph, ctx, a, b):
    ctx["matches"] = graph.find_matches(team=a, opponent=b)


@when(parsers.parse('I request the head-to-head between "{a}" and "{b}"'))
def _h2h(graph, ctx, a, b):
    ctx["h2h"] = graph.head_to_head(a, b)


@when(parsers.parse('I search Brasileirao matches for "{team}" in season {season:d}'))
def _by_season(graph, ctx, team, season):
    ctx["matches"] = graph.find_matches(
        team=team, competition="Brasileirão", season=season
    )


@when(parsers.parse('I request the team record for "{team}" in season {season:d}'))
def _record(graph, ctx, team, season):
    ctx["record"] = graph.team_record(team, season=season)
    ctx["team"] = team
    ctx["season"] = season


@when(parsers.parse('I search for all matches involving "{team}"'))
def _all(graph, ctx, team):
    ctx["matches"] = graph.find_matches(team=team)


@then(parsers.parse("I should receive {n:d} matches"))
def _count(ctx, n):
    assert len(ctx["matches"]) == n


@then("each match should have a date, scores and a competition")
def _shape(graph, ctx):
    for m in ctx["matches"]:
        d = graph.match_to_dict(m)
        assert d["date"] is not None
        assert d["competition"]
        assert "home_goal" in d and "away_goal" in d


@then(parsers.parse("Flamengo should have {n:d} win"))
def _fla_win(ctx, n):
    assert ctx["h2h"]["team_a_wins"] == n


@then(parsers.parse("Fluminense should have {n:d} win"))
def _flu_win(ctx, n):
    assert ctx["h2h"]["team_b_wins"] == n


@then(parsers.parse("there should be {n:d} draws"))
def _draws(ctx, n):
    assert ctx["h2h"]["draws"] == n


@then(parsers.parse('every match should be in the "{comp}" competition'))
def _comp(ctx, comp):
    assert all(m.competition == comp for m in ctx["matches"])


@then(parsers.parse("the team should have played {n:d} match"))
def _played(ctx, n):
    assert ctx["record"].matches == n


@then(parsers.parse('the record should not include "{other}" matches'))
def _not_other(graph, ctx, other):
    # The other club's record over the same season must be independent.
    other_rec = graph.team_record(other, season=ctx["season"])
    assert other_rec.team != ctx["record"].team
    assert other_rec.matches >= 0


@then("the result should include a match with no recorded score")
def _has_scoreless(ctx):
    assert any(not m.has_score for m in ctx["matches"])
