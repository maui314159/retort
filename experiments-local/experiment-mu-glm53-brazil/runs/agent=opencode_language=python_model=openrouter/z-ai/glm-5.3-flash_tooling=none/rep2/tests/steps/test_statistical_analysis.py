"""BDD step definitions for Feature: Statistical Analysis."""

from __future__ import annotations

import time

from pytest_bdd import parsers, scenarios, then, when

from tests.steps.helpers import World

scenarios("../../features/statistical_analysis.feature")


@when(parsers.parse('I request the head-to-head record of "{team_a}" and "{team_b}"'))
def h2h(world: World, team_a: str, team_b: str) -> None:
    world.result = world.engine.head_to_head(team_a, team_b)


@when(parsers.parse('I request the biggest victories in "{competition}"'))
def biggest(world: World, competition: str) -> None:
    world.result = world.engine.biggest_wins(competition=competition, limit=20)


@when(parsers.parse('I request statistics for competition "{competition}"'))
def comp_stats(world: World, competition: str) -> None:
    world.result = world.engine.competition_statistics(competition)


@when(parsers.parse('I search the knowledge graph for "{query}"'))
def kg_search(world: World, query: str) -> None:
    world.result = world.engine.graph_search(query, limit=50)


@when(parsers.parse('I request the graph neighbors of "{node}"'))
def kg_neighbors(world: World, node: str) -> None:
    world.result = world.engine.graph_neighbors(node, limit=50)


@when(parsers.parse('I run the search for team "{team}" in season {season:d}'))
def perf_search(world: World, team: str, season: int) -> None:
    world.params = {"team": team, "season": season}


@then("the record should have at least one match")
def record_played(world: World) -> None:
    assert world.result["record"]["played"] >= 1


@then("wins and draws should add up to the matches played")
def record_sums(world: World) -> None:
    record = world.result["record"]
    assert (
        record["team_a_wins"] + record["team_b_wins"] + record["draws"]
        == record["played"]
    )


@then("I should receive a list of matches")
def matches_list(world: World) -> None:
    assert world.result["count"] > 0
    assert world.result["matches"]


@then("each match margin should be greater than or equal to the next one")
def margins_ordered(world: World) -> None:
    margins = [
        abs(m["home_goals"] - m["away_goals"]) for m in world.result["matches"]
    ]
    assert margins == sorted(margins, reverse=True)


@then(parsers.parse("the average goals per match should be between {low:d} and {high:d}"))
def avg_goals(world: World, low: float, high: float) -> None:
    avg = world.result["statistics"]["average_goals_per_match"]
    assert low <= avg <= high


@then("I should receive graph nodes")
def nodes_received(world: World) -> None:
    assert world.result["count"] > 0


@then(parsers.parse('every node name should contain "{fragment}"'))
def node_names(world: World, fragment: str) -> None:
    for node in world.result["nodes"]:
        assert fragment.lower() in node["name"].lower()


@then("I should receive relationships such as played or participates_in")
def relationships(world: World) -> None:
    rel_types = set(world.result["relationships"])
    assert rel_types & {"PLAYED", "PARTICIPATES_IN", "BEAT", "DREW_WITH", "LOST_TO"}


@then("the query should complete within 2 seconds")
def performance(world: World) -> None:
    start = time.perf_counter()
    result = world.engine.search_matches(
        team=world.params["team"], season=world.params["season"], limit=20
    )
    elapsed = time.perf_counter() - start
    assert result["count"] > 0
    assert elapsed < 2.0, f"query took {elapsed:.2f}s"
