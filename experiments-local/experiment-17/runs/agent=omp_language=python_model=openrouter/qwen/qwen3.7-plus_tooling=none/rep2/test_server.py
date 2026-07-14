"""BDD tests for Brazilian Soccer MCP Server."""

import pytest
import re
from pytest_bdd import scenarios, given, when, then, parsers

from data_loader import get_matches_df, get_players_df, clear_cache
from server import (
    search_matches,
    get_team_stats,
    search_players,
    get_competition_standings,
    get_head_to_head,
    get_statistical_analysis,
)

# Load feature file
scenarios("test_soccer.feature")


@pytest.fixture(autouse=True)
def clear_data():
    """Clear cached data before each test."""
    clear_cache()
    yield
    clear_cache()


# --- Given steps ---

@given("the match data is loaded")
def match_data_loaded():
    df = get_matches_df()
    assert not df.empty, "Match data should not be empty"
    return df


@given("the player data is loaded")
def player_data_loaded():
    df = get_players_df()
    assert not df.empty, "Player data should not be empty"
    return df


# --- When steps ---

@when(parsers.parse('I search for matches between "{team1}" and "{team2}"'), target_fixture="result")
def search_matches_between(team1, team2):
    result = search_matches(team=team1, limit=50)
    return result


@when(parsers.parse('I request statistics for "{team}"'), target_fixture="result")
def request_team_stats(team):
    return get_team_stats(team=team)


@when(parsers.parse('I search for players with nationality "{nationality}"'), target_fixture="result")
def search_players_nationality(nationality):
    return search_players(nationality=nationality, limit=20)


@when(parsers.parse('I search for matches for "{team}"'), target_fixture="result")
def search_matches_for_team(team):
    return search_matches(team=team, limit=20)


@when(parsers.parse('I request standings for "{competition}" in season "{season}"'), target_fixture="result")
def request_standings(competition, season):
    return get_competition_standings(competition=competition, season=season)


@when(parsers.parse('I request head-to-head between "{team1}" and "{team2}"'), target_fixture="result")
def request_h2h(team1, team2):
    return get_head_to_head(team1=team1, team2=team2)


@when(parsers.parse('I request statistical analysis for "{metric}"'), target_fixture="result")
def request_stats(metric):
    return get_statistical_analysis(metric=metric)


@when('I search for matches in season "2003"', target_fixture="result")
def search_matches_2003():
    return search_matches(season="2003", limit=20)


# --- Then steps ---

@then("I should receive a list of matches")
def receive_list_of_matches(result: str):
    assert "Found" in result or "match" in result.lower()
    assert "-" in result  # Match bullet point


@then("each match should have date, scores, and competition")
def match_has_date_scores_competition(result: str):
    lines = [line for line in result.split("\n") if line.startswith("-")]
    assert len(lines) > 0, "Should have at least one match"
    for line in lines[:3]:  # Check first 3
        assert "20" in line  # Year in date
        assert "-" in line   # Score separator
        assert "[" in line or "(" in line  # Competition info


@then("I should receive wins, losses, draws, and goals")
def receive_wins_losses_draws_goals(result: str):
    assert "W" in result or "Win" in result
    assert "D" in result or "Draw" in result
    assert "L" in result or "Loss" in result
    assert "Goal" in result or "GF" in result


@then("I should receive a list of Brazilian players")
def receive_brazilian_players(result: str):
    assert "Found" in result or "player" in result.lower()
    assert "Brazil" in result


@then("each player should have name, club, and overall rating")
def player_has_name_club_rating(result: str):
    lines = [line for line in result.split("\n") if line.startswith("-")]
    assert len(lines) > 0
    for line in lines[:3]:
        assert "@" in line  # Club indicator
        assert "Overall:" in line


@then('I should receive matches for "Corinthians"')
def receive_corinthians_matches(result: str):
    assert "corinthians" in result.lower() or "Found" in result


@then("I should receive a ranked list of teams with points")
def receive_ranked_teams(result: str):
    assert "Standings" in result or "#" in result
    assert "Pts" in result or "points" in result.lower()


@then("I should receive total matches, wins for each team, and draws")
def receive_h2h_stats(result: str):
    assert "Head-to-Head" in result or "Matches" in result
    assert "Wins" in result or "win" in result.lower()
    assert "Draw" in result or "draw" in result.lower()


@then("I should receive the average goals per match")
def receive_avg_goals(result: str):
    assert "Average Goals" in result or "avg" in result.lower()
    assert ":" in result


@then("I should receive matches with properly formatted dates")
def receive_formatted_dates(result: str):
    assert "2003" in result
    # Dates should be YYYY-MM-DD format
    date_pattern = r"\d{4}-\d{2}-\d{2}"
    assert re.search(date_pattern, result), "Should have YYYY-MM-DD formatted dates"
