"""BDD step definitions for Feature: Match Queries."""

from __future__ import annotations

import pytest
from pytest_bdd import parsers, scenarios, then, when

from tests.steps.helpers import World

scenarios("../../features/match_queries.feature")


@when(parsers.parse('I search for matches between "{team_a}" and "{team_b}"'))
def search_between(world: World, team_a: str, team_b: str) -> None:
    world.result = world.engine.search_matches(team=team_a, opponent=team_b, limit=50)
    world.params = {"team_a": team_a, "team_b": team_b}


@when(parsers.parse('I search for matches for team "{team}"'))
def search_team(world: World, team: str) -> None:
    world.result = world.engine.search_matches(team=team, limit=50)


@when(parsers.parse('I search for matches for team "{team}" in season {season:d}'))
def search_team_season(world: World, team: str, season: int) -> None:
    world.result = world.engine.search_matches(team=team, season=season, limit=50)
    world.params = {"team": team, "season": season}


@when(parsers.parse('I search for matches for team "{team}" from "{date_from}" to "{date_to}"'))
def search_team_dates(world: World, team: str, date_from: str, date_to: str) -> None:
    world.result = world.engine.search_matches(team=team, date_from=date_from, date_to=date_to, limit=100)
    world.params = {"team": team, "date_from": date_from, "date_to": date_to}


@when(parsers.parse('I search for matches for team "{team}" in competition "{competition}"'))
def search_team_comp(world: World, team: str, competition: str) -> None:
    world.result = world.engine.search_matches(team=team, competition=competition, limit=100)


@when(parsers.parse('I search for matches in competition "{competition}" with stage "{stage}"'))
def search_stage(world: World, competition: str, stage: str) -> None:
    world.result = world.engine.search_matches(competition=competition, stage=stage, limit=100)


@then("I should receive a list of matches")
def receive_matches(world: World) -> None:
    assert isinstance(world.result["matches"], list)
    assert world.result["count"] > 0


@then("each match should have date, scores and competition")
def match_fields(world: World) -> None:
    for match in world.result["matches"]:
        assert match["date"] is not None
        assert match["home_goals"] is not None
        assert match["away_goals"] is not None
        assert match["competition"]


@then("the result should include a head-to-head record")
def h2h_included(world: World) -> None:
    assert "head_to_head" in world.result
    record = world.result["head_to_head"]
    assert record["played"] == world.result["total_matches"]


@then(parsers.parse('the total number of matches should be the same as for "{team_a}" and "{team_b}"'))
def variant_parity(world: World, team_a: str, team_b: str) -> None:
    baseline = world.engine.search_matches(team=team_a, opponent=team_b, limit=1)
    assert world.result["total_matches"] == baseline["total_matches"]


@then(parsers.parse('every match should be from season "{season}"'))
def all_season(world: World, season: str) -> None:
    assert world.result["count"] > 0
    for match in world.result["matches"]:
        assert match["season"] == int(season)


@then(parsers.parse('every match date should fall between "{date_from}" and "{date_to}"'))
def all_dates_in_range(world: World, date_from: str, date_to: str) -> None:
    assert world.result["count"] > 0
    for match in world.result["matches"]:
        assert date_from <= match["date"] <= date_to


@then(parsers.parse('every match should be from competition "{competition}"'))
def all_comp(world: World, competition: str) -> None:
    assert world.result["count"] > 0
    for match in world.result["matches"]:
        assert match["competition"] == competition


@then(parsers.parse('every match should have stage "{stage}"'))
def all_stage(world: World, stage: str) -> None:
    assert world.result["count"] > 0
    for match in world.result["matches"]:
        assert match["stage"] == stage


@then("the response should indicate no team was found")
def no_team(world: World) -> None:
    summary = world.result["summary"].lower()
    assert "no team matching" in summary
    assert world.result["count"] == 0
