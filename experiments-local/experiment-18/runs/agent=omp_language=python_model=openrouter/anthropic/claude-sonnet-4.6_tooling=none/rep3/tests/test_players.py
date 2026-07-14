"""
================================================================================
tests.test_players
================================================================================
Context:
    BDD step definitions for tests/features/players.feature. Covers player
    name search, nationality filtering, overall-rating sorting and position
    filtering against the FIFA player database.
================================================================================
"""

from pytest_bdd import parsers, scenarios, then, when

scenarios("features/players.feature")


@when(parsers.parse('I search for the player "{name}"'))
def _search(graph, context, name):
    context["players"] = graph.search_players(name)


@when(parsers.parse('I list players from "{nat}"'))
def _by_nat(graph, context, nat):
    context["players"] = graph.players_by_nationality(nat)
    context["nationality"] = nat


@when(parsers.parse('I request the top {n:d} players from "{nat}"'))
def _top_nat(graph, context, n, nat):
    context["players"] = graph.top_players(nationality=nat, limit=n)


@when(parsers.parse('I request the top {n:d} "{pos}" players from "{nat}"'))
def _top_pos(graph, context, n, pos, nat):
    context["players"] = graph.top_players(nationality=nat, position=pos, limit=n)
    context["position"] = pos


@then("I should find at least one player")
def _at_least_one(context):
    assert len(context["players"]) >= 1


@then("the top result should be Brazilian")
def _top_brazilian(context):
    assert context["players"][0].nationality == "Brazil"


@then("I should receive many players")
def _many(context):
    assert len(context["players"]) > 50


@then(parsers.parse('every returned player should have nationality "{nat}"'))
def _all_nat(context, nat):
    assert context["players"]
    for p in context["players"]:
        assert p.nationality == nat


@then("the results should be sorted by overall rating descending")
def _sorted_desc(context):
    overalls = [p.overall or 0 for p in context["players"]]
    assert overalls == sorted(overalls, reverse=True)
    assert len(overalls) >= 1


@then(parsers.parse('every returned player should play position "{pos}"'))
def _all_pos(context, pos):
    assert context["players"]
    for p in context["players"]:
        assert p.position.upper() == pos.upper()
