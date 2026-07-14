"""
Pytest-BDD step definitions for Brazilian Soccer MCP features.

This file wires the Gherkin scenarios in tests/features/ to the query
engine.  Assertions focus on behavioral outcomes (e.g. records returned,
correct sorting, normalized names) rather than exact counts, because the
provided datasets may be updated over time.
"""

from __future__ import annotations

import json
import re
from typing import Any

import pandas as pd
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from brazilian_soccer_mcp.data_store import DataStore
from brazilian_soccer_mcp import queries


# ---------------------------------------------------------------------------
# Load all feature files
# ---------------------------------------------------------------------------
scenarios("../features")


# ---------------------------------------------------------------------------
# Shared context object passed between steps
# ---------------------------------------------------------------------------
@pytest.fixture
def context() -> dict[str, Any]:
    """Mutable context shared within a single scenario."""
    return {}


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------
@given("the match data is loaded")
def given_match_data_loaded(data_store: DataStore, context: dict[str, Any]) -> None:
    """Ensure the unified match DataFrame is available."""
    context["data_store"] = data_store
    assert len(data_store.matches) > 0, "Match data should not be empty"


@given("the player data is loaded")
def given_player_data_loaded(data_store: DataStore, context: dict[str, Any]) -> None:
    """Ensure the player DataFrame is available."""
    context["data_store"] = data_store
    assert len(data_store.players) > 0, "Player data should not be empty"


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------
@when(parsers.parse('I search for matches between "{team_a}" and "{team_b}"'))
def when_search_matches_between(
    team_a: str, team_b: str, context: dict[str, Any]
) -> None:
    result = queries.find_matches(
        store=context["data_store"],
        team=team_a,
        opponent=team_b,
        limit=100,
        response_format="json",
    )
    context["result"] = result


@when(parsers.parse('I search for matches for "{team}" in season "{season}"'))
def when_search_matches_for_team_in_season(
    team: str, season: str, context: dict[str, Any]
) -> None:
    result = queries.find_matches(
        store=context["data_store"],
        team=team,
        season=int(season),
        limit=100,
        response_format="json",
    )
    context["result"] = result


@when(parsers.parse('I search for "{competition}" matches'))
def when_search_matches_by_competition(
    competition: str, context: dict[str, Any]
) -> None:
    result = queries.find_matches(
        store=context["data_store"],
        competition=competition,
        limit=100,
        response_format="json",
    )
    context["result"] = result


@when(parsers.parse('I request statistics for "{team}" in season "{season}"'))
def when_request_team_stats(
    team: str, season: str, context: dict[str, Any]
) -> None:
    result = queries.get_team_stats(
        store=context["data_store"],
        team=team,
        season=int(season),
        response_format="json",
    )
    context["result"] = result


@when(parsers.parse('I compare "{team_a}" and "{team_b}" head-to-head'))
def when_compare_head_to_head(
    team_a: str, team_b: str, context: dict[str, Any]
) -> None:
    result = queries.get_head_to_head(
        store=context["data_store"],
        team_a=team_a,
        team_b=team_b,
        limit=100,
        response_format="json",
    )
    context["result"] = result


@when("I list all teams")
def when_list_all_teams(context: dict[str, Any]) -> None:
    result = queries.list_teams(
        store=context["data_store"], response_format="json"
    )
    context["result"] = result


@when(parsers.parse('I search for players with nationality "{nationality}"'))
def when_search_players_by_nationality(
    nationality: str, context: dict[str, Any]
) -> None:
    result = queries.search_players(
        store=context["data_store"],
        nationality=nationality,
        limit=100,
        response_format="json",
    )
    context["result"] = result


@when(parsers.parse('I search for players at club "{club}"'))
def when_search_players_by_club(
    club: str, context: dict[str, Any]
) -> None:
    result = queries.search_players(
        store=context["data_store"],
        club=club,
        limit=100,
        response_format="json",
    )
    context["result"] = result


@when(parsers.parse('I request the top "{limit}" Brazilian players'))
def when_request_top_brazilian_players(
    limit: str, context: dict[str, Any]
) -> None:
    result = queries.top_brazilian_players(
        store=context["data_store"],
        limit=int(limit),
        response_format="json",
    )
    context["result"] = result


@when(
    parsers.parse(
        'I request standings for season "{season}" competition "{competition}"'
    )
)
def when_request_standings(
    season: str, competition: str, context: dict[str, Any]
) -> None:
    result = queries.get_standings(
        store=context["data_store"],
        season=int(season),
        competition=competition,
        response_format="json",
    )
    context["result"] = result


@when(
    parsers.parse(
        'I request the winner for season "{season}" competition "{competition}"'
    )
)
def when_request_winner(
    season: str, competition: str, context: dict[str, Any]
) -> None:
    result = queries.get_competition_winners(
        store=context["data_store"],
        season=int(season),
        competition=competition,
        response_format="json",
    )
    context["result"] = result


@when(parsers.parse('I request average goals for "{competition}"'))
def when_request_average_goals(
    competition: str, context: dict[str, Any]
) -> None:
    result = queries.get_average_goals(
        store=context["data_store"],
        competition=competition,
        response_format="json",
    )
    context["result"] = result


@when(parsers.parse('I request the biggest "{limit}" wins'))
def when_request_biggest_wins(limit: str, context: dict[str, Any]) -> None:
    result = queries.get_biggest_wins(
        store=context["data_store"],
        limit=int(limit),
        response_format="json",
    )
    context["result"] = result


@when(parsers.parse('I compare season "{season_a}" and season "{season_b}"'))
def when_compare_seasons(
    season_a: str, season_b: str, context: dict[str, Any]
) -> None:
    result = queries.compare_seasons(
        store=context["data_store"],
        season_a=int(season_a),
        season_b=int(season_b),
        response_format="json",
    )
    context["result"] = result


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------
@then("I should receive a list of matches")
def then_receive_matches(context: dict[str, Any]) -> None:
    result = context["result"]
    assert isinstance(result, dict)
    assert result["total"] > 0, "Expected at least one match"
    assert result["returned"] > 0


@then("each match should have date, scores, and competition")
def then_matches_have_required_fields(context: dict[str, Any]) -> None:
    result = context["result"]
    matches = result["matches"]
    for match in matches:
        assert pd.notna(match.get("date")), "Match should have a date"
        assert pd.notna(match.get("home_goal")), "Match should have home_goal"
        assert pd.notna(match.get("away_goal")), "Match should have away_goal"
        assert match.get("competition"), "Match should have a competition"


@then(parsers.parse('I should receive matches only from season "{season}"'))
def then_matches_only_from_season(season: str, context: dict[str, Any]) -> None:
    result = context["result"]
    matches = result["matches"]
    assert all(
        str(m.get("season")) == season for m in matches
    ), "All matches should belong to the requested season"


@then(parsers.parse('all returned matches should have competition "{competition}"'))
def then_matches_have_competition(
    competition: str, context: dict[str, Any]
) -> None:
    result = context["result"]
    matches = result["matches"]
    assert all(
        m.get("competition") == competition for m in matches
    ), "All matches should belong to the requested competition"


@then("I should receive wins, losses, draws, and goals")
def then_team_stats_present(context: dict[str, Any]) -> None:
    result = context["result"]
    assert isinstance(result, dict)
    for key in ("wins", "losses", "draws", "goals_for", "goals_against"):
        assert key in result, f"Missing key: {key}"


@then(parsers.parse('the team name should be normalized to "{expected}"'))
def then_team_name_normalized(expected: str, context: dict[str, Any]) -> None:
    result = context["result"]
    assert result["team"] == expected


@then("I should receive a win count for each team and draws")
def then_head_to_head_counts(context: dict[str, Any]) -> None:
    result = context["result"]
    assert isinstance(result, dict)
    assert "total_matches" in result
    assert result["total_matches"] > 0
    keys = list(result.keys())
    win_keys = [k for k in keys if k.endswith("_wins")]
    assert len(win_keys) == 2, "Should have win counts for both teams"
    assert "draws" in result


@then(parsers.parse('I should see canonical team names including "{team}"'))
def then_team_list_includes(team: str, context: dict[str, Any]) -> None:
    result = context["result"]
    assert team in result["teams"], f"Expected {team} in team list"


@then("all returned players should be Brazilian")
def then_players_are_brazilian(context: dict[str, Any]) -> None:
    result = context["result"]
    players = result["players"]
    assert all(
        str(p.get("nationality")).strip().lower() == "brazil"
        for p in players
    ), "All players should be Brazilian"


@then(parsers.parse('the returned players should include players from {club}'))
def then_players_include_club(club: str, context: dict[str, Any]) -> None:
    result = context["result"]
    players = result["players"]
    clubs = {str(p.get("club") or p.get("club_raw") or "").lower() for p in players}
    assert club.lower() in clubs, f"Expected {club} players"


@then("the players should be sorted by overall rating descending")
def then_players_sorted_by_overall(context: dict[str, Any]) -> None:
    result = context["result"]
    players = result["players"]
    overalls = [p["overall"] for p in players]
    assert overalls == sorted(overalls, reverse=True), "Players should be sorted by overall"


@then("I should receive a table sorted by points descending")
def then_standings_sorted(context: dict[str, Any]) -> None:
    result = context["result"]
    standings = result["standings"]
    points = [s["points"] for s in standings]
    assert points == sorted(points, reverse=True), "Standings should be sorted by points"


@then("the first team should be the champion")
def then_first_team_champion(context: dict[str, Any]) -> None:
    result = context["result"]
    standings = result["standings"]
    assert len(standings) > 0
    assert standings[0]["team"], "Champion team should be present"


@then(parsers.parse('the winner should be "{expected}"'))
def then_winner_is(expected: str, context: dict[str, Any]) -> None:
    result = context["result"]
    assert result["winner"] == expected, f"Expected winner {expected}, got {result['winner']}"


@then("the result should contain a positive average goals value")
def then_average_goals_positive(context: dict[str, Any]) -> None:
    result = context["result"]
    assert result["average_goals_per_match"] > 0


@then("the returned matches should be ordered by goal margin descending")
def then_biggest_wins_ordered(context: dict[str, Any]) -> None:
    result = context["result"]
    matches = result["matches"]
    margins = [
        abs(int(m["home_goal"]) - int(m["away_goal"])) for m in matches
    ]
    assert margins == sorted(margins, reverse=True), "Matches should be ordered by margin"


@then("I should receive statistics for both seasons")
def then_both_seasons_present(context: dict[str, Any]) -> None:
    result = context["result"]
    assert "season_a" in result
    assert "season_b" in result
    assert result["season_a"]["matches"] >= 0
    assert result["season_b"]["matches"] >= 0
