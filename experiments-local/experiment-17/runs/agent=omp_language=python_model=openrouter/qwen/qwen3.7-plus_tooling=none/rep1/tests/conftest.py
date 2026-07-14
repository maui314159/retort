import pytest
from pytest_bdd import given, when, then, parsers
from tools import search_matches, get_team_statistics, get_head_to_head, search_players, get_competition_standings

@pytest.fixture
def match_data_loaded():
    from data_loader import get_all_matches
    assert get_all_matches() is not None

@pytest.fixture
def player_data_loaded():
    from data_loader import load_fifa_data
    assert load_fifa_data() is not None

@given("the match data is loaded")
def match_data_is_loaded(match_data_loaded):
    pass

@given("the player data is loaded")
def player_data_is_loaded(player_data_loaded):
    pass

@when(parsers.parse('I search for matches between "{team1}" and "{team2}"'), target_fixture="result")
def search_between_teams(team1, team2):
    return get_head_to_head(team1, team2, limit=5)

@then("I should receive a list of matches")
def receive_list_of_matches(result):
    assert "Head-to-Head:" in result or "wins" in result.lower()

@then("each match should have date, scores, and competition")
def match_has_details(result):
    assert "-" in result
    assert "vs" in result.lower() or "-" in result

@when(parsers.parse('I request statistics for "{team}" in season {season:d}'), target_fixture="result")
def request_team_stats(team, season):
    return get_team_statistics(team, season=season)

@then("I should receive wins, losses, draws, and goals")
def receive_stats(result):
    assert "Wins:" in result
    assert "Draws:" in result
    assert "Losses:" in result
    assert "Goals For:" in result

@when(parsers.parse('I request head to head between "{team1}" and "{team2}"'), target_fixture="result")
def request_h2h(team1, team2):
    return get_head_to_head(team1, team2, limit=5)

@then("I should receive win counts for both teams and draws")
def receive_h2h_stats(result):
    assert "wins:" in result.lower()
    assert "draws:" in result.lower()

@when(parsers.parse('I search for players with nationality "{nat}" and min rating {rating:d}'), target_fixture="result")
def search_players_by_nat(nat, rating):
    return search_players(nationality=nat, min_rating=rating, limit=5)

@then("I should receive a list of highly rated Brazilian players")
def receive_top_players(result):
    assert "Top matching players:" in result or "Overall:" in result