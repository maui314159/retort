"""BDD step definitions for Feature: Player Queries."""

from __future__ import annotations

from pytest_bdd import parsers, scenarios, then, when

from tests.steps.helpers import World

scenarios("../../features/player_queries.feature")


@when(parsers.parse('I search for the player "{name}"'))
def search_player(world: World, name: str) -> None:
    world.result = world.engine.search_players(name=name, limit=10)


@when(parsers.parse('I request the profile of "{name}"'))
def profile(world: World, name: str) -> None:
    world.result = world.engine.player_profile(name)


@when(parsers.parse('I search for players with nationality "{nationality}" and minimum overall {min_overall:d}'))
def search_nat(world: World, nationality: str, min_overall: int) -> None:
    world.result = world.engine.search_players(nationality=nationality, min_overall=min_overall, limit=50)


@when(parsers.parse('I search for players with club "{club}"'))
def search_club(world: World, club: str) -> None:
    world.result = world.engine.search_players(club=club, limit=50)


@then("I should receive matching players")
def players_found(world: World) -> None:
    assert world.result["count"] > 0
    assert world.result["players"]


@then("the top result should have a name, nationality, club and overall rating")
def top_fields(world: World) -> None:
    top = world.result["players"][0]
    for field in ("name", "nationality", "club", "overall"):
        assert top[field] is not None


@then("I should receive the player's attributes")
def profile_fields(world: World) -> None:
    player = world.result["player"]
    for field in ("name", "age", "nationality", "overall", "potential", "position"):
        assert player[field] is not None


@then("the profile should include skill ratings")
def profile_skills(world: World) -> None:
    skills = world.result["player"]["skills"]
    assert "Dribbling" in skills or "GKDiving" in skills
    assert len(skills) >= 10


@then(parsers.parse('every player should be Brazilian with overall at least {min_overall:d}'))
def brazilian_min_overall(world: World, min_overall: int) -> None:
    assert world.result["count"] > 0
    for player in world.result["players"]:
        assert player["nationality"] == "Brazil"
        assert player["overall"] >= min_overall


@then(parsers.parse('every player should belong to "{club}"'))
def club_members(world: World, club: str) -> None:
    assert world.result["count"] > 0
    for player in world.result["players"]:
        assert club.lower() in player["club"].lower()


@then("the response should indicate no player was found")
def no_player(world: World) -> None:
    assert "no player" in world.result["summary"].lower()
