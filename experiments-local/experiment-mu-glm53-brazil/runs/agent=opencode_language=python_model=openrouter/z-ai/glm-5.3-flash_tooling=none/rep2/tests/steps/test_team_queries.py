"""BDD step definitions for Feature: Team Queries."""

from __future__ import annotations

from pytest_bdd import parsers, scenarios, then, when

from tests.steps.helpers import World

scenarios("../../features/team_queries.feature")


@when(parsers.parse('I request statistics for "{team}" in season "{season}"'))
def stats_season(world: World, team: str, season: str) -> None:
    world.result = world.engine.team_statistics(team, season=int(season))


@when(parsers.parse('I request statistics for "{team}" in season "{season}" in competition "{competition}"'))
def stats_season_comp(world: World, team: str, season: str, competition: str) -> None:
    world.result = world.engine.team_statistics(team, competition=competition, season=int(season))


@when(parsers.parse('I request statistics for "{team}" in season "{season}" in competition "{competition}" at venue "{venue}"'))
def stats_comp_venue(world: World, team: str, season: str, competition: str, venue: str) -> None:
    world.result = world.engine.team_statistics(
        team, competition=competition, season=int(season), venue=venue
    )


@when(parsers.parse('I compare "{team_a}" and "{team_b}"'))
def compare(world: World, team_a: str, team_b: str) -> None:
    world.result = world.engine.team_comparison(team_a, team_b)


@when(parsers.parse('I request an overview for "{team}"'))
def overview(world: World, team: str) -> None:
    world.result = world.engine.team_overview(team)


@then("I should receive wins, losses, draws and goals")
def record_fields(world: World) -> None:
    stats = world.result["statistics"]
    for field in ("played", "wins", "draws", "losses", "goals_for", "goals_against"):
        assert field in stats
    assert stats["wins"] + stats["draws"] + stats["losses"] == stats["played"]


@then(parsers.parse("the team should have played {expected:d} matches"))
def played_matches(world: World, expected: int) -> None:
    assert world.result["statistics"]["played"] == expected


@then(parsers.parse('the resolved team should be "{team}"'))
def resolved_team(world: World, team: str) -> None:
    assert world.result["query"]["team"] == team


@then("I should receive statistics for both teams")
def both_teams(world: World) -> None:
    assert world.result["team_a"]["played"] > 0
    assert world.result["team_b"]["played"] > 0


@then("I should receive a head-to-head record")
def h2h(world: World) -> None:
    assert world.result["head_to_head"]["played"] > 0


@then("the overview should include competitions and seasons")
def overview_content(world: World) -> None:
    assert world.result["competitions"]
    assert world.result["seasons"]


@then("the overview should include FIFA players for the club")
def overview_players(world: World) -> None:
    assert world.result["player_count"] > 0
    assert world.result["players"]


@then("the response should indicate no team was found")
def no_team(world: World) -> None:
    assert "no team matching" in world.result["summary"].lower()
