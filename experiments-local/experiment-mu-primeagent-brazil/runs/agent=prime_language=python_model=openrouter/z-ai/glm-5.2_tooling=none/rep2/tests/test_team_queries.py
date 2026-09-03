"""
Context block
=============
Brazilian Soccer MCP Server - BDD Step Definitions: Team Queries
"""

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/team_queries.feature")


@pytest.fixture
def ctx():
    return {}


@given("the match data is loaded", target_fixture="match_data")
def match_data_loaded(engine):
    return engine


@when(parsers.parse('I request statistics for "{team}" in season {season:d}'),
      target_fixture="stats")
def team_stats(match_data, ctx, team, season):
    ctx["stats"] = match_data.team_statistics(team, season=season,
                                              competition="brasileirao")
    return ctx["stats"]


@when(parsers.parse('I request home statistics for "{team}" in season {season:d}'),
      target_fixture="stats")
def team_home_stats(match_data, ctx, team, season):
    ctx["stats"] = match_data.team_statistics(team, season=season,
                                              competition="brasileirao",
                                              venue="home")
    return ctx["stats"]


@when(parsers.parse('I ask which competitions "{team}" played in'),
      target_fixture="competitions")
def team_competitions(match_data, ctx, team):
    ctx["competitions"] = match_data.team_competitions(team)
    return ctx["competitions"]


@when(parsers.parse('I compare "{team_a}" and "{team_b}" head to head'),
      target_fixture="h2h")
def head_to_head(match_data, ctx, team_a, team_b):
    ctx["h2h"] = match_data.head_to_head(team_a, team_b)
    return ctx["h2h"]


@then("I should receive wins, draws, losses and goals")
def assert_stats_keys(stats):
    for key in ("wins", "draws", "losses", "goals_for", "goals_against"):
        assert key in stats


@then("the win rate should be a percentage between 0 and 100")
def assert_win_rate(stats):
    assert 0 <= stats["win_rate"] <= 100


@then("the venue should be home")
def assert_venue(stats):
    assert stats["venue"] == "home"


@then("the matches count should equal wins plus draws plus losses")
def assert_match_count(stats):
    assert stats["matches"] == stats["wins"] + stats["draws"] + stats["losses"]


@then("I should receive a list of competitions with match counts")
def assert_competitions(competitions):
    assert isinstance(competitions, list)
    assert len(competitions) >= 1
    for c in competitions:
        assert "competition" in c and "matches" in c
        assert c["matches"] > 0


@then("I should receive win counts for both teams and a draw count")
def assert_h2h_counts(h2h):
    for key in ("team_a_wins", "team_b_wins", "draws"):
        assert key in h2h


@then("the total matches should equal the sum of wins and draws")
def assert_h2h_total(h2h):
    wins = h2h["team_a_wins"] + h2h["team_b_wins"]
    assert h2h["matches"] == wins + h2h["draws"]
