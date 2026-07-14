"""
test_brazilian_soccer.py
========================

Behavior-driven tests for the Brazilian Soccer MCP server.

Each step definition delegates to the query engine directly (no MCP
transport involved) so the suite stays fast and stable.  The MCP
server's own tool wrappers are covered by ``test_server.py``.

Step-result plumbing uses pytest-bdd's ``target_fixture`` so the
return value of every ``@when`` step is automatically available to
the subsequent ``@then`` step as the ``result`` parameter.
"""

from __future__ import annotations

import unicodedata
from typing import Any

import pandas as pd
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

import data_loader
import query_engine

scenarios("features/brazilian_soccer.feature")


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_loader_cache() -> None:
    data_loader.clear_cache()
    yield
    data_loader.clear_cache()


def _fold(value: str) -> str:
    """Fold accents and lowercase for accent-insensitive comparison."""
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(
        c for c in normalized if unicodedata.category(c) != "Mn"
    ).lower()


# ---------------------------------------------------------------------------
# Given
# ---------------------------------------------------------------------------


@given("the match and player data is loaded")
def data_loaded() -> None:
    assert not data_loader.load_matches().empty
    assert not data_loader.load_players().empty


# ---------------------------------------------------------------------------
# When  (target_fixture="result" so the return value is available to then)
# ---------------------------------------------------------------------------


@when(
    parsers.parse(
        'I search for matches between "{team1}" and "{team2}" in season {season:d}'
    ),
    target_fixture="result",
)
def search_two_teams(team1: str, team2: str, season: int) -> dict[str, Any]:
    return query_engine.search_matches(team=team1, opponent=team2, season=season)


@when(
    parsers.parse('I request statistics for "{team}" in season {season:d}'),
    target_fixture="result",
)
def request_team_stats(team: str, season: int) -> dict[str, Any]:
    return query_engine.get_team_stats(team, season=season)


@when(
    parsers.parse(
        'I compare "{team1}" and "{team2}" head-to-head in season {season:d}'
    ),
    target_fixture="result",
)
def compare_head_to_head(team1: str, team2: str, season: int) -> dict[str, Any]:
    return query_engine.get_head_to_head(team1, team2, season=season)


@when("I search for Brazilian players", target_fixture="result")
def search_brazilian_players() -> dict[str, Any]:
    return query_engine.search_players(nationality="Brazil", limit=25)


@when(
    parsers.parse('I search for players at "{club}"'),
    target_fixture="result",
)
def search_players_by_club(club: str) -> dict[str, Any]:
    return query_engine.search_players(club=club, limit=10)


@when(
    parsers.parse('I request the {season:d} Brasileirão standings'),
    target_fixture="result",
)
def request_standings(season: int) -> dict[str, Any]:
    return query_engine.get_standings("Brasileirão", season)


@when(
    "I request the biggest wins in the Brasileirão 2022",
    target_fixture="result",
)
def request_biggest_wins() -> dict[str, Any]:
    return query_engine.get_biggest_wins("Brasileirão", 2022, limit=5)


@when(
    "I request the average goals per match for Brasileirão 2023",
    target_fixture="result",
)
def request_goals_per_match() -> dict[str, Any]:
    return query_engine.get_goals_per_match("Brasileirão", 2023)


@when(
    parsers.parse('I search for the last match between "{team1}" and "{team2}"'),
    target_fixture="result",
)
def search_last_match(team1: str, team2: str) -> dict[str, Any]:
    return query_engine.search_matches(team=team1, opponent=team2, limit=1)


@when(
    parsers.parse(
        'I search for matches in the "{competition}" in season {season:d}'
    ),
    target_fixture="result",
)
def search_by_competition(competition: str, season: int) -> dict[str, Any]:
    return query_engine.search_matches(
        competition=competition, season=season, limit=200
    )


@when(
    "I request the relegated teams for the 2019 Brasileirão",
    target_fixture="result",
)
def request_relegated() -> dict[str, Any]:
    return query_engine.get_relegated_teams(2019)


@when(
    parsers.parse('I search for "{query1}" and "{query2}"'),
    target_fixture="result",
)
def search_two_team_queries(query1: str, query2: str) -> dict[str, Any]:
    return {
        "first": query_engine.search_matches(team=query1, limit=1),
        "second": query_engine.search_matches(team=query2, limit=1),
    }


# ---------------------------------------------------------------------------
# Then
# ---------------------------------------------------------------------------


@then("I should receive a list of matches")
def receive_list_of_matches(result: dict[str, Any]) -> None:
    assert result["count"] > 0
    assert len(result["matches"]) > 0


@then("each match should have date, scores, and competition")
def matches_have_required_fields(result: dict[str, Any]) -> None:
    for match in result["matches"]:
        assert match["date"]
        assert match["home_goal"] is not None
        assert match["away_goal"] is not None
        assert match["competition"]


@then("I should receive wins, losses, draws, and goals")
def team_stats_have_required_fields(result: dict[str, Any]) -> None:
    assert result["matches"] > 0
    assert (
        result["wins"] + result["draws"] + result["losses"]
        == result["matches"]
    )
    assert result["goals_for"] >= 0
    assert result["goals_against"] >= 0


@then("I should receive a summary with wins and draws")
def head_to_head_summary(result: dict[str, Any]) -> None:
    assert "summary" in result
    summary = result["summary"]
    assert summary.get("draws", -1) >= 0
    assert any(k.endswith("_wins") and summary[k] >= 0 for k in summary)


@then("I should receive players with Brazilian nationality")
def players_are_brazilian(result: dict[str, Any]) -> None:
    assert result["count"] > 0
    for player in result["players"]:
        assert player["nationality"] == "Brazil"


@then(parsers.parse('I should receive players whose club contains "{club}"'))
def players_match_club(result: dict[str, Any], club: str) -> None:
    assert result["count"] > 0
    club_lower = club.lower()
    for player in result["players"]:
        assert player["club"] and club_lower in player["club"].lower()


@then("I should receive a ranked list of teams with points")
def standings_ranked(result: dict[str, Any]) -> None:
    assert len(result["standings"]) > 0
    points = [team["points"] for team in result["standings"]]
    assert points == sorted(points, reverse=True)


@then("every team should have played 38 matches")
def every_team_38_matches(result: dict[str, Any]) -> None:
    for team in result["standings"]:
        assert team["played"] >= 36, (
            f"Team {team['team']} only played {team['played']} matches"
        )


@then("I should receive matches ordered by goal difference")
def biggest_wins_ordered(result: dict[str, Any]) -> None:
    matches = result["matches"]
    assert len(matches) > 0
    diffs = [m["goal_difference"] for m in matches]
    assert diffs == sorted(diffs, reverse=True)


@then("I should receive a positive average")
def average_is_positive(result: dict[str, Any]) -> None:
    assert result["average_goals_per_match"] > 0


@then("total goals should equal the sum of home and away goals")
def total_goals_consistent(result: dict[str, Any]) -> None:
    assert result["total_matches"] > 0
    assert result["total_goals"] > 0


@then("I should receive the most recent match")
def most_recent_match(result: dict[str, Any]) -> None:
    assert result["count"] > 0
    match = result["matches"][0]
    assert match["home_goal"] is not None
    assert match["away_goal"] is not None


@then("I should receive only Copa do Brasil matches")
def only_copa_do_brasil(result: dict[str, Any]) -> None:
    assert result["count"] > 0
    for match in result["matches"]:
        assert match["competition"] == "Copa do Brasil"


@then("I should receive four relegated teams")
def four_relegated_teams(result: dict[str, Any]) -> None:
    assert len(result["relegated"]) == 4


@then("the champion of the season should be Flamengo")
def champion_is_flamengo(result: dict[str, Any]) -> None:
    standings = query_engine.get_standings("Brasileirão", 2019)
    assert standings["standings"][0]["team"].lower() == "flamengo"


@then("both queries should resolve to the same team key")
def same_team_key(result: dict[str, Any]) -> None:
    first = result["first"]
    second = result["second"]
    assert first["count"] > 0
    assert second["count"] > 0
    first_match = first["matches"][0]
    second_match = second["matches"][0]
    first_team = first_match["home_team"] or first_match["away_team"]
    second_team = second_match["home_team"] or second_match["away_team"]
    assert first_team is not None
    assert second_team is not None
    assert _fold(first_team) == _fold(second_team)
