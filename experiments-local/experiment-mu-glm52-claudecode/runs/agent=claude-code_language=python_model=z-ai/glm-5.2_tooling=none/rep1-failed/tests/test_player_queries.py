"""BDD step definitions for the Player Queries feature."""

from __future__ import annotations

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from brazilian_soccer_mcp import queries

scenarios("features/player_queries.feature")


@given("the match data is loaded")
def match_data_loaded(kg):
    assert kg is not None and len(kg.dataset.players) > 0


@when(
    'I search for players of nationality "{nationality}"',
    target_fixture="result",
)
def search_by_nationality(kg, context, nationality):
    res = queries.search_players(kg, nationality=nationality, limit=200)
    context["result"] = res
    return res


@when(
    'I search for players at club "{club}" sorted by rating',
    target_fixture="result",
)
def search_at_club(kg, context, club):
    res = queries.search_players(kg, club=club, limit=50)
    context["result"] = res
    return res


@when(
    'I search for players named "{name}"',
    target_fixture="result",
)
def search_by_name(kg, context, name):
    res = queries.search_players(kg, name=name, limit=200)
    context["result"] = res
    return res


@when(
    'I search for players in position "{position}"',
    target_fixture="result",
)
def search_by_position(kg, context, position):
    res = queries.search_players(kg, position=position, limit=200)
    context["result"] = res
    return res


@when(
    "I search for Brazilian players with overall at least {threshold:d}",
    target_fixture="result",
)
def search_brazil_above(kg, context, threshold):
    res = queries.search_players(
        kg, nationality="Brazil", min_overall=threshold, limit=200
    )
    context["result"] = res
    return res


@then("I should receive a list of players")
def player_list(context):
    res = context["result"]
    assert isinstance(res, dict)
    assert res.get("total", 0) >= 1
    assert isinstance(res.get("players"), list)


@then("every player should be Brazilian")
def all_brazilian(context):
    for p in context["result"]["players"]:
        assert p["nationality"] == "Brazil"


@then("the first player should have the highest overall rating")
def first_is_highest(context):
    players = context["result"]["players"]
    assert players, "no players returned"
    top = players[0]
    for p in players[1:]:
        assert top["overall"] >= p["overall"]


@then('every player name should contain "Gabriel"')
def names_contain_gabriel(context):
    for p in context["result"]["players"]:
        assert "Gabriel" in p["name"]


@then('every player should have position "ST"')
def all_position_st(context):
    for p in context["result"]["players"]:
        assert p["position"] == "ST"


@then("every player should have overall at least 85")
def all_overall_ge_85(context):
    for p in context["result"]["players"]:
        assert p["overall"] >= 85


@then("Neymar Jr should be among the top-rated Brazilians")
def neymar_top(context):
    names = [p["name"] for p in context["result"]["players"]]
    assert "Neymar Jr" in names
