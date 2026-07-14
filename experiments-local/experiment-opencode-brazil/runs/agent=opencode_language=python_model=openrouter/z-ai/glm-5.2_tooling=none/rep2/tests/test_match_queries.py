# ============================================================================
# Context: Brazilian Soccer MCP Server benchmark.
# BDD step definitions for match_queries.feature. Implements Given/When/Then
# steps that exercise the QueryEngine match and team-stat methods.
# ----------------------------------------------------------------------------
from __future__ import annotations

import pytest
from pytest_bdd import when, then, parsers, scenarios

from brazilian_soccer_mcp import QueryEngine

scenarios("features/match_queries.feature")


@when(
    parsers.parse('I search for matches between "{team_a}" and "{team_b}"'),
    target_fixture="matches_result",
)
def search_matches_between(engine: QueryEngine, team_a, team_b):
    return engine.find_matches(team=team_a, opponent=team_b)


@when(
    parsers.parse('I search for matches in competition "{competition}"'),
    target_fixture="matches_result",
)
def search_matches_in_competition(engine: QueryEngine, competition):
    return engine.find_matches(competition=competition, limit=50)


@when(
    parsers.parse('I request statistics for "{team}" in season "{season:d}"'),
    target_fixture="stats_result",
)
def request_stats(engine: QueryEngine, team, season):
    return engine.team_stats(team, season=season)


@when(
    parsers.parse('I compare "{team_a}" and "{team_b}" head-to-head'),
    target_fixture="h2h_result",
)
def compare_h2h(engine: QueryEngine, team_a, team_b):
    return engine.head_to_head(team_a, team_b)


# ----------------------------------------------------------------------------
# Then steps
# ----------------------------------------------------------------------------
@then("I should receive a list of matches")
def should_receive_matches(matches_result):
    assert isinstance(matches_result, list)
    assert len(matches_result) > 0, "Expected at least one match"


@then("each match should have date, scores, and competition")
def each_match_well_formed(matches_result):
    for m in matches_result:
        assert "date" in m
        assert "home_goals" in m
        assert "away_goals" in m
        assert "competition" in m
        assert "home_team" in m
        assert "away_team" in m


@then("I should receive wins, losses, draws, and goals")
def stats_have_fields(stats_result):
    for field in ("wins", "losses", "draws", "goals_for", "goals_against"):
        assert field in stats_result, f"Missing field: {field}"


@then("the played count should be greater than zero")
def stats_played_positive(stats_result):
    assert stats_result["played"] > 0


@then("I should receive wins, draws, and goals for both teams")
def h2h_fields(h2h_result):
    for field in ("team_a_wins", "team_b_wins", "draws", "team_a_goals", "team_b_goals"):
        assert field in h2h_result


@then("the matches played should be greater than zero")
def h2h_played_positive(h2h_result):
    assert h2h_result["matches_played"] > 0


@then(parsers.parse('every returned match should belong to "{competition}"'))
def all_in_competition(matches_result, competition):
    assert matches_result, "Expected non-empty result"
    for m in matches_result:
        assert m["competition"] == competition, (
            f"Match {m} not in {competition}"
        )
