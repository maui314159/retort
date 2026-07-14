"""BDD step definitions for Player Queries feature.

Context block
-------------
Implements Given/When/Then steps for ``player_queries.feature``.
"""
from __future__ import annotations

from pytest_bdd import scenarios, given, when, then, parsers

scenarios("features/player_queries.feature")


@given("the player data is loaded", target_fixture="player_ctx")
def player_data_loaded(loader):
    assert not loader.players.empty
    return {"loader": loader, "result": None}


@when(parsers.parse('I search for players of nationality "{nationality}"'),
      target_fixture="player_ctx")
def search_by_nationality(player_ctx, queries, nationality):
    player_ctx["result"] = queries["search_players"](
        player_ctx["loader"], nationality=nationality, limit=200
    )
    return player_ctx


@when(parsers.parse('I request the top {n:d} players at "{club}"'),
      target_fixture="player_ctx")
def top_at_club(player_ctx, queries, n, club):
    player_ctx["result"] = queries["top_players_at_club"](
        player_ctx["loader"], club, limit=n
    )
    return player_ctx


@when(parsers.parse('I search for players named "{name}"'),
      target_fixture="player_ctx")
def search_by_name(player_ctx, queries, name):
    player_ctx["result"] = queries["search_players"](
        player_ctx["loader"], name=name
    )
    return player_ctx


@when(parsers.parse('I search for Brazilian players with minimum overall {overall:d}'),
      target_fixture="player_ctx")
def search_brazil_min(player_ctx, queries, overall):
    player_ctx["result"] = queries["search_players"](
        player_ctx["loader"], nationality="Brazil", min_overall=overall
    )
    return player_ctx


@then("I should receive a list of players")
def players_list(player_ctx):
    assert isinstance(player_ctx["result"], list)
    assert len(player_ctx["result"]) > 0


@then("every player should be Brazilian")
def players_brazilian(player_ctx):
    for p in player_ctx["result"]:
        assert p["nationality"] == "Brazil"


@then("I should receive at most 5 players")
def at_most_five(player_ctx):
    assert len(player_ctx["result"]) <= 5


@then("the players should be sorted by overall rating descending")
def sorted_overall(player_ctx):
    ratings = [p["overall"] for p in player_ctx["result"]]
    assert ratings == sorted(ratings, reverse=True)


@then("I should receive at least one player")
def at_least_one(player_ctx):
    assert len(player_ctx["result"]) >= 1


@then("the first result should be Neymar Jr")
def first_is_neymar(player_ctx):
    assert "neymar" in player_ctx["result"][0]["name"].lower()


@then("every player should have an overall rating of at least 85")
def overall_at_least_85(player_ctx):
    for p in player_ctx["result"]:
        assert p["overall"] >= 85
