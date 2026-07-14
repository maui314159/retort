"""
BDD step definitions for Brazilian Soccer MCP Server.

Run with: pytest tests/test_brazilian_soccer.py
"""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, then, when

from query_engine import (
    get_biggest_wins,
    get_goals_per_match,
    get_head_to_head,
    get_standings,
    get_team_stats,
    search_matches,
    search_players,
)

scenarios("features/brazilian_soccer.feature")


# ---------------------------------------------------------------------------
# Shared given steps
# ---------------------------------------------------------------------------


@given("the match data is loaded")
def match_data_loaded():
    """Loading happens lazily inside query_engine functions."""
    pass


@given("the player data is loaded")
def player_data_loaded():
    """Loading happens lazily inside query_engine functions."""
    pass


# ---------------------------------------------------------------------------
# When steps (all publish their output into the shared "result" fixture)
# ---------------------------------------------------------------------------


@when(
    parsers.parse('I search for matches between "{team1}" and "{team2}" in season {season:d}'),
    target_fixture="result",
)
def search_two_teams(team1: str, team2: str, season: int):
    return search_matches(team=team1, opponent=team2, season=season)


@when(
    parsers.parse('I request statistics for "{team}" in season {season:d}'),
    target_fixture="result",
)
def request_team_stats(team: str, season: int):
    return get_team_stats(team, season=season)


@when(
    parsers.parse('I compare "{team1}" and "{team2}" head-to-head in season {season:d}'),
    target_fixture="result",
)
def compare_head_to_head(team1: str, team2: str, season: int):
    return get_head_to_head(team1, team2, season=season)


@when("I search for Brazilian players", target_fixture="result")
def search_brazilian_players():
    return search_players(nationality="Brazil", limit=10)


@when(parsers.parse('I search for players at "{club}"'), target_fixture="result")
def search_players_by_club(club: str):
    return search_players(club=club, limit=10)


@when(
    parsers.parse('I request the {season:d} Brasileirão standings'),
    target_fixture="result",
)
def request_standings(season: int):
    return get_standings("Brasileirão", season)


@when(
    parsers.parse('I request the biggest wins in the Brasileirão {season:d}'),
    target_fixture="result",
)
def request_biggest_wins(season: int):
    return get_biggest_wins("Brasileirão", season, limit=5)


@when(
    parsers.parse('I request the average goals per match for Brasileirão {season:d}'),
    target_fixture="result",
)
def request_goals_per_match(season: int):
    return get_goals_per_match("Brasileirão", season)


@when(
    parsers.parse('I search for the last match between "{team1}" and "{team2}"'),
    target_fixture="result",
)
def search_last_match(team1: str, team2: str):
    return search_matches(team=team1, opponent=team2, limit=1)


@when(
    parsers.parse('I search for matches in the "{competition}" in season {season:d}'),
    target_fixture="result",
)
def search_by_competition(competition: str, season: int):
    return search_matches(competition=competition, season=season, limit=100)


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------


@then("I should receive a list of matches")
def receive_list_of_matches(result):
    assert result["count"] > 0
    assert len(result["matches"]) > 0


@then("each match should have date, scores, and competition")
def matches_have_required_fields(result):
    for match in result["matches"]:
        assert match["date"]
        assert match["home_goal"] is not None
        assert match["away_goal"] is not None
        assert match["competition"]


@then("I should receive wins, losses, draws, and goals")
def team_stats_have_required_fields(result):
    assert result["matches"] > 0
    assert "wins" in result
    assert "losses" in result
    assert "draws" in result
    assert result["goals_for"] >= 0
    assert result["goals_against"] >= 0


@then("I should receive a summary with wins and draws")
def head_to_head_summary(result):
    assert "summary" in result
    summary = result["summary"]
    assert summary["total"] > 0
    assert any(k.endswith("_wins") and summary[k] >= 0 for k in summary)


@then("I should receive players with Brazilian nationality")
def players_are_brazilian(result):
    assert result["count"] > 0
    for player in result["players"]:
        assert player["nationality"] == "Brazil"


@then(parsers.parse('I should receive players whose club contains "{club}"'))
def players_match_club(result, club: str):
    assert result["count"] > 0
    club_lower = club.lower()
    for player in result["players"]:
        assert player["club"] and club_lower in player["club"].lower()


@then("I should receive a ranked list of teams with points")
def standings_ranked(result):
    assert len(result["standings"]) > 0
    points = [team["points"] for team in result["standings"]]
    assert points == sorted(points, reverse=True)


@then("I should receive matches ordered by goal difference")
def biggest_wins_ordered(result):
    matches = result["matches"]
    assert len(matches) > 0
    diffs = [m["goal_difference"] for m in matches]
    assert diffs == sorted(diffs, reverse=True)


@then("I should receive a positive average")
def average_is_positive(result):
    assert result["average_goals_per_match"] > 0


@then("I should receive the most recent match")
def most_recent_match(result):
    assert result["count"] > 0
    match = result["matches"][0]
    assert match["date"]
    assert match["home_goal"] is not None
    assert match["away_goal"] is not None


@then("I should receive only Copa do Brasil matches")
def only_copa_do_brasil(result):
    assert result["count"] > 0
    for match in result["matches"]:
        assert match["competition"] == "Copa do Brasil"
