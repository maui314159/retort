"""
================================================================================
Context
--------------------------------------------------------------------------------
Module  : tests.test_players
Purpose : BDD steps for features/players.feature - FIFA player search by name,
          nationality, club and position, plus rating-descending ordering.
================================================================================
"""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/players.feature")


@given("the soccer knowledge graph is loaded", target_fixture="graph")
def _loaded(sample_graph):
    return sample_graph


@when(parsers.parse('I search for the player "{name}"'))
def _by_name(graph, ctx, name):
    ctx["players"] = graph.find_players(name=name)


@when(parsers.parse('I search for players from "{nat}"'))
def _by_nat(graph, ctx, nat):
    ctx["players"] = graph.find_players(nationality=nat)


@when(parsers.parse('I search for players at the club "{club}"'))
def _by_club(graph, ctx, club):
    ctx["players"] = graph.find_players(club=club)


@when(parsers.parse('I search for "{nat}" players in position "{pos}"'))
def _by_pos(graph, ctx, nat, pos):
    ctx["players"] = graph.find_players(nationality=nat, position=pos)


@then(parsers.parse('I should find a player named "{name}"'))
def _found(ctx, name):
    assert any(p.name == name for p in ctx["players"])


@then("the player should have an overall rating")
def _rating(ctx):
    assert ctx["players"][0].overall is not None


@then("every returned player should be Brazilian")
def _all_br(ctx):
    assert ctx["players"]
    assert all(p.nationality == "Brazil" for p in ctx["players"])


@then("the players should be sorted by overall rating descending")
def _sorted(ctx):
    overalls = [p.overall or 0 for p in ctx["players"]]
    assert overalls == sorted(overalls, reverse=True)


@then(parsers.parse('every returned player should belong to "{club}"'))
def _all_club(ctx, club):
    assert ctx["players"]
    assert all(club.lower() in p.club.lower() for p in ctx["players"])


@then(parsers.parse('every returned player should play position "{pos}"'))
def _all_pos(ctx, pos):
    assert ctx["players"]
    assert all(p.position == pos for p in ctx["players"])
