"""BDD step definitions for the Player Queries feature."""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, when, then

scenarios("../features/player_queries.feature")


@given("the player data is loaded")
def loaded_store(store):
    return store


@when(parsers.parse('I search for players with nationality "{nationality}"'), target_fixture="result")
def search_by_nationality(store, nationality):
    return store.search_players(nationality=nationality, limit=100)


@when(parsers.parse('I look up the player "{name}"'), target_fixture="result")
def lookup_player(store, name):
    try:
        return {"player": store.get_player(name)}
    except LookupError as exc:
        return {"error": exc}


@when(parsers.parse('I search for players at club "{club}"'), target_fixture="result")
def players_at_club(store, club):
    return store.players_at_club(club)


@when(parsers.parse('I search for Brazilian "{position}" players rated at least {rating:d}'), target_fixture="result")
def search_position(store, position, rating):
    return store.search_players(nationality="brazil", position=position,
                                min_overall=rating, limit=50)


@then("I should receive a list of players")
def assert_player_list(result):
    assert isinstance(result.get("players"), list)
    assert result["total"] > 0


@then("every player should be Brazilian")
def assert_brazilian(result):
    for p in result["players"]:
        assert p["nationality"].lower() == "brazil"


@then("players should be sorted by overall rating descending")
def assert_sorted_desc(result):
    overalls = [p["overall"] for p in result["players"]]
    assert overalls == sorted(overalls, reverse=True)


@then("I should receive the player profile")
def assert_profile(result):
    assert result.get("player"), result
    for field in ("name", "overall", "potential", "club", "skills"):
        assert field in result["player"]


@then(parsers.parse('the player should play for "{club}"'))
def assert_club(result, club):
    assert result["player"]["club"] == club


@then("the players should have an average rating")
def assert_average(result):
    assert result["total_players"] > 0
    assert 40 <= result["average_overall"] <= 99


@then("every player should be a striker rated at least 80")
def assert_strikers(result):
    assert result["total"] > 0
    for p in result["players"]:
        assert p["position"] == "ST"
        assert p["overall"] >= 80


@then("a not-found error should be raised")
def assert_not_found(result):
    assert isinstance(result, dict) and "error" in result
