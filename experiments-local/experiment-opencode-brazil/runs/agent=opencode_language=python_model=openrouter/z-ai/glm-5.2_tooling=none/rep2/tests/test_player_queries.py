# ============================================================================
# Context: Brazilian Soccer MCP Server benchmark.
# BDD step definitions for player_queries.feature.
# ----------------------------------------------------------------------------
from __future__ import annotations

from pytest_bdd import when, then, parsers, scenarios

from brazilian_soccer_mcp import QueryEngine

scenarios("features/player_queries.feature")


@when(
    parsers.parse('I request the top {n:d} Brazilian players'),
    target_fixture="players_result",
)
def top_brazilian_players(engine: QueryEngine, n):
    return engine.top_brazilian_players(limit=n)


@when(
    parsers.parse('I search for players named "{name}"'),
    target_fixture="players_result",
)
def search_by_name(engine: QueryEngine, name):
    return engine.search_players(name=name)


@when(
    parsers.parse('I search for players with minimum overall rating {rating:d}'),
    target_fixture="players_result",
)
def search_min_rating(engine: QueryEngine, rating):
    return engine.search_players(min_overall=rating, limit=50)


@then(parsers.parse("I should receive up to {n:d} players"))
def up_to_n_players(players_result, n):
    assert isinstance(players_result, list)
    assert len(players_result) <= n


@then("each player should have nationality Brazil")
def each_brazilian(players_result):
    assert players_result, "Expected at least one player"
    for p in players_result:
        assert p["Nationality"] == "Brazil"


@then("the players should be sorted by overall rating descending")
def sorted_desc(players_result):
    ratings = [p["Overall"] for p in players_result]
    assert ratings == sorted(ratings, reverse=True)


@then(parsers.parse("I should receive at least one player"))
def at_least_one(players_result):
    assert len(players_result) >= 1


@then(parsers.parse('the first player should be named "{name}"'))
def first_named(players_result, name):
    assert players_result[0]["Name"] == name


@then(parsers.parse("every returned player should have an overall rating of at least {rating:d}"))
def all_above_rating(players_result, rating):
    assert players_result
    for p in players_result:
        assert float(p["Overall"]) >= rating
