"""BDD step definitions for Feature: Competition Queries."""

from __future__ import annotations

from pytest_bdd import parsers, scenarios, then, when

from tests.steps.helpers import World

scenarios("../../features/competition_queries.feature")


@when(parsers.parse('I request the standings for "{competition}" season "{season}"'))
def standings(world: World, competition: str, season: str) -> None:
    world.result = world.engine.league_standings(competition, int(season))


@when(parsers.parse('I request statistics for competition "{competition}"'))
def comp_stats(world: World, competition: str) -> None:
    world.result = world.engine.competition_statistics(competition)


@then(parsers.parse('the champion should be "{team}"'))
def champion(world: World, team: str) -> None:
    assert world.result["standings"][0]["team"] == team


@then(parsers.parse("the champion should have {points:d} points"))
def champion_points(world: World, points: int) -> None:
    assert world.result["standings"][0]["points"] == points


@then(parsers.parse("the standings should contain {teams:d} teams"))
def team_count(world: World, teams: int) -> None:
    assert len(world.result["standings"]) == teams


@then(parsers.parse("every team should have played {matches:d} matches"))
def matches_played(world: World, matches: int) -> None:
    for row in world.result["standings"]:
        assert row["played"] == matches


@then(parsers.parse("the standings should mark {n:d} relegated teams"))
def relegated(world: World, n: int) -> None:
    zones = [row.get("zone") for row in world.result["standings"]]
    assert zones.count("Relegation") == n


@then("I should receive average goals per match and home win rate")
def agg_stats(world: World) -> None:
    stats = world.result["statistics"]
    assert stats["average_goals_per_match"] is not None
    assert 0 <= stats["home_win_rate"] <= 100


@then(parsers.parse("the number of matches should be greater than {minimum:d}"))
def match_minimum(world: World, minimum: int) -> None:
    assert world.result["statistics"]["matches"] > minimum


@then("the response should indicate no matches were found")
def no_matches(world: World) -> None:
    assert "no matches found" in world.result["summary"].lower()
