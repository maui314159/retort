"""
Context block
=============
Brazilian Soccer MCP Server - BDD Step Definitions: Player Queries
"""

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/player_queries.feature")


@pytest.fixture
def ctx():
    return {}


@given("the player data is loaded", target_fixture="player_data")
def player_data_loaded(engine):
    return engine


@when('I search for players of nationality "Brazil"', target_fixture="players")
def search_brazilian(player_data, ctx):
    ctx["players"] = player_data.search_players(nationality="Brazil", limit=None)
    return ctx["players"]


@when(parsers.parse('I search for players named "{name}"'), target_fixture="players")
def search_name(player_data, ctx, name):
    ctx["players"] = player_data.search_players(name=name, limit=50)
    return ctx["players"]


@when("I request the top 5 Brazilian players", target_fixture="players")
def top_brazilian(player_data, ctx):
    ctx["players"] = player_data.top_brazilian_players(limit=5)
    return ctx["players"]


@when(parsers.parse('I request players at club "{club}"'), target_fixture="players")
def players_at_club(player_data, ctx, club):
    ctx["players"] = player_data.players_at_club(club)
    return ctx["players"]


@then("I should receive players")
def assert_players(players):
    assert len(players) > 0


@then("every returned player should be Brazilian")
def assert_brazilian(players):
    assert all(p["nationality"] == "Brazil" for p in players)


@then("the players should be sorted by overall rating descending")
def assert_sorted(players):
    ratings = [p["overall"] for p in players]
    assert ratings == sorted(ratings, reverse=True)


@then("I should receive at least one player")
def assert_at_least_one(players):
    assert len(players) >= 1


@then("the first player should be Neymar Jr")
def assert_neymar(players):
    assert players[0]["name"] == "Neymar Jr"


@then("the highest rated player should be Neymar Jr")
def assert_top_neymar(players):
    top = max(players, key=lambda p: p["overall"])
    assert top["name"] == "Neymar Jr"


@then("the highest overall rating should be 92")
def assert_top_rating(players):
    assert max(p["overall"] for p in players) == 92


@then(parsers.parse('every returned player should play for {club}'))
def assert_club(players, club):
    from brazilian_soccer_mcp.normalizer import display_name
    dn = display_name(club)
    assert all(p["club"] == dn for p in players), {p["club"] for p in players}
