"""
BDD step definitions for player_queries.feature
"""

from __future__ import annotations

import json

from pytest_bdd import given, when, then, scenarios

scenarios("player_queries.feature")


@given("the player data is loaded")
def player_data_loaded():
    pass


@when('I search for players named "Neymar"')
def search_neymar(invoker):
    invoker.result = json.loads(invoker.search_players(name="Neymar"))


@then("I should find at least one player")
def found_player(invoker):
    assert isinstance(invoker.result, list)
    assert len(invoker.result) >= 1


@when('I search for players from "Brazil"')
def search_brazilians(invoker):
    invoker.result = json.loads(invoker.search_players(nationality="Brazil"))


@then("I should receive players with Brazilian nationality")
def brazilian_players(invoker):
    assert len(invoker.result) > 0
    for p in invoker.result:
        assert "Brazil" in p.get("Nationality", "")


@when('I search for players at club "Santos"')
def search_santos_players(invoker):
    invoker.result = json.loads(invoker.search_players(club="Santos"))


@then("all results should play for a club containing Santos")
def santos_players(invoker):
    assert len(invoker.result) > 0
    for p in invoker.result:
        assert "Santos" in p.get("Club", "")


@when("I search for Brazilian players with min overall 85")
def search_top_brazilians(invoker):
    invoker.result = json.loads(invoker.search_players(nationality="Brazil", min_overall=85))


@then("all results should have overall rating at least 85")
def min_85_overall(invoker):
    assert len(invoker.result) > 0
    for p in invoker.result:
        assert p.get("Overall", 0) >= 85
