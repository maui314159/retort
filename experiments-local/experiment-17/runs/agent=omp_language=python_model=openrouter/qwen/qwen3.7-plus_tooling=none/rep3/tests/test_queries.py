import pytest
from pytest_bdd import scenarios, given, when, then, parsers
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from data_loader import load_data
from mcp_server import get_head_to_head, get_team_stats, search_matches

scenarios('features/queries.feature')

@pytest.fixture(scope="session")
def loaded_data():
    return load_data()

@given("the match data is loaded")
def match_data_loaded(loaded_data):
    assert loaded_data[0] is not None
    return loaded_data

@when(parsers.parse('I search for matches between "{team1}" and "{team2}"'), target_fixture="query_result")
def search_matches_between(team1, team2):
    result = get_head_to_head(team1, team2)
    return json.loads(result)

@then("I should receive a list of matches")
def receive_list_of_matches(query_result):
    assert "error" not in query_result
    assert "recent_matches" in query_result
    assert isinstance(query_result["recent_matches"], list)

@then("each match should have date, scores, and competition")
def match_has_required_fields(query_result):
    for match in query_result["recent_matches"]:
        assert "-" in match
        assert "(" in match

@when(parsers.parse('I request statistics for "{team}" in season {season:d}'), target_fixture="query_result")
def request_team_stats(team, season):
    result = get_team_stats(team, season=season)
    return json.loads(result)

@then("I should receive wins, losses, draws, and goals")
def receive_team_stats(query_result):
    assert "error" not in query_result
    assert "wins" in query_result
    assert "losses" in query_result
    assert "draws" in query_result
    assert "goals_for" in query_result
    assert "goals_against" in query_result
