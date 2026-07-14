"""
Brazilian Soccer MCP Server — BDD Test Suite

Uses pytest-bdd (Gherkin Given/When/Then) to verify the five required
capability categories from TASK.md "Required Capabilities":
  1. Match Queries
  2. Team Queries
  3. Player Queries
  4. Competition Queries
  5. Statistical Analysis

Plus data-quality requirements from TASK.md "Data Quality Notes":
  - Team name normalisation
  - Multi-format date handling
"""

from __future__ import annotations

import pytest
from pytest_bdd import given, when, then, parsers, scenarios

from data_loader import (
    search_matches,
    get_team_stats,
    get_head_to_head,
    search_players,
    get_competition_standings,
    get_statistics,
    list_teams,
    list_competitions,
    list_seasons,
    normalize_team,
)

scenarios("match_queries.feature")
scenarios("team_queries.feature")
scenarios("player_queries.feature")
scenarios("competition_queries.feature")
scenarios("statistical_analysis.feature")
scenarios("team_normalisation.feature")
scenarios("data_coverage.feature")


# ---------------------------------------------------------------------------
# Shared context fixtures
# ---------------------------------------------------------------------------


class MatchQueryContext:
    def __init__(self):
        self.result = None


class TeamQueryContext:
    def __init__(self):
        self.result = None


class PlayerQueryContext:
    def __init__(self):
        self.result = None


class CompetitionQueryContext:
    def __init__(self):
        self.result = None


class StatsQueryContext:
    def __init__(self):
        self.result = None


class TeamNormContext:
    def __init__(self):
        self.result = None


class DataCoverageContext:
    def __init__(self):
        self.teams = None
        self.competitions = None
        self.seasons = None


@pytest.fixture
def ctx():
    return MatchQueryContext()


@pytest.fixture
def team_ctx():
    return TeamQueryContext()


@pytest.fixture
def player_ctx():
    return PlayerQueryContext()


@pytest.fixture
def comp_ctx():
    return CompetitionQueryContext()


@pytest.fixture
def stats_ctx():
    return StatsQueryContext()


@pytest.fixture
def norm_ctx():
    return TeamNormContext()


@pytest.fixture
def coverage_ctx():
    return DataCoverageContext()


# ---------------------------------------------------------------------------
# Feature: Match Queries
# ---------------------------------------------------------------------------


@given("the match data is loaded", target_fixture="ctx")
def match_data_loaded(ctx):
    matches = search_matches(limit=1)
    assert len(matches) >= 1, "No match data loaded"
    return ctx


@when(parsers.parse('I search for matches between "{team_a}" and "{team_b}"'))
def search_head_to_head(ctx, team_a, team_b):
    ctx.result = search_matches(team=team_a, opponent=team_b)


@then("I should receive a list of matches")
def verify_matches_list(ctx):
    assert isinstance(ctx.result, list)
    assert len(ctx.result) > 0


@then("each match should have date, scores, and competition")
def verify_match_fields(ctx):
    for m in ctx.result:
        assert "date" in m, f"Missing 'date' in {m}"
        assert "home_goal" in m, f"Missing 'home_goal' in {m}"
        assert "away_goal" in m, f"Missing 'away_goal' in {m}"
        assert "competition" in m, f"Missing 'competition' in {m}"


@when(parsers.parse('I search for matches with team "{team}" in season {season:d}'))
def search_team_season(ctx, team, season):
    ctx.result = search_matches(team=team, season=season)


@then(parsers.parse("I should receive at least {count:d} match"))
def verify_min_matches(ctx, count):
    assert len(ctx.result) >= count, f"Expected >= {count} matches, got {len(ctx.result)}"


@then(parsers.parse('each match should involve team containing "{team_partial}"'))
def verify_team_in_matches(ctx, team_partial):
    for m in ctx.result:
        home = (m.get("home_team_norm") or "").lower()
        away = (m.get("away_team_norm") or "").lower()
        assert team_partial.lower() in home or team_partial.lower() in away, \
            f"Team '{team_partial}' not found in {m}"


@when(parsers.parse('I search for matches in competition "{competition}"'))
def search_by_competition(ctx, competition):
    ctx.result = search_matches(competition=competition, limit=10)


@then(parsers.parse('each match competition should contain "{comp_partial}"'))
def verify_competition(ctx, comp_partial):
    for m in ctx.result:
        assert comp_partial.lower() in (m.get("competition") or "").lower(), \
            f"Competition '{comp_partial}' not found in {m}"


# ---------------------------------------------------------------------------
# Feature: Team Queries
# ---------------------------------------------------------------------------


@given("the team data is available", target_fixture="team_ctx")
def team_data_available(team_ctx):
    teams = list_teams()
    assert len(teams) > 0, "No teams found"
    return team_ctx


@when(parsers.parse('I request statistics for "{team}" in season {season:d}'))
def get_team_stats_query(team_ctx, team, season):
    team_ctx.result = get_team_stats(team=team, season=season)


@then("I should receive wins, losses, draws, and goals")
def verify_team_stats_fields(team_ctx):
    r = team_ctx.result
    assert "wins" in r
    assert "losses" in r
    assert "draws" in r
    assert "goals_for" in r
    assert "goals_against" in r


@then("the total matches should equal wins plus draws plus losses")
def verify_team_stats_consistency(team_ctx):
    r = team_ctx.result
    assert r["wins"] + r["draws"] + r["losses"] == r["matches"]


@when(parsers.parse('I compare "{team_a}" and "{team_b}" head-to-head'))
def h2h_query(team_ctx, team_a, team_b):
    team_ctx.result = get_head_to_head(team_a=team_a, team_b=team_b)


@then("I should receive head-to-head results")
def verify_h2h(team_ctx):
    r = team_ctx.result
    assert "team_a_wins" in r
    assert "team_b_wins" in r
    assert "draws" in r
    assert "matches" in r
    assert r["total_matches"] == r["team_a_wins"] + r["team_b_wins"] + r["draws"]


# ---------------------------------------------------------------------------
# Feature: Player Queries
# ---------------------------------------------------------------------------


@given("the player data is loaded", target_fixture="player_ctx")
def player_data_loaded(player_ctx):
    players = search_players(limit=1)
    assert len(players) > 0, "No player data loaded"
    return player_ctx


@when(parsers.parse('I search for players with nationality "{nationality}"'))
def search_by_nationality(player_ctx, nationality):
    player_ctx.result = search_players(nationality=nationality, limit=20)


@then("I should receive a list of players")
def verify_players_list(player_ctx):
    assert isinstance(player_ctx.result, list)
    assert len(player_ctx.result) > 0


@then(parsers.parse('each player nationality should contain "{nat_partial}"'))
def verify_player_nationality(player_ctx, nat_partial):
    for p in player_ctx.result:
        assert nat_partial.lower() in (p.get("Nationality") or "").lower(), \
            f"Nationality '{nat_partial}' not found in {p}"


@when(parsers.parse('I search for players at club "{club}"'))
def search_by_club(player_ctx, club):
    player_ctx.result = search_players(club=club, limit=20)


@then(parsers.parse('each player club should contain "{club_partial}"'))
def verify_player_club(player_ctx, club_partial):
    for p in player_ctx.result:
        assert club_partial.lower() in (p.get("Club") or "").lower(), \
            f"Club '{club_partial}' not found in {p}"


# ---------------------------------------------------------------------------
# Feature: Competition Queries
# ---------------------------------------------------------------------------


@given("the competition data is available", target_fixture="comp_ctx")
def comp_data_available(comp_ctx):
    comps = list_competitions()
    assert len(comps) > 0, "No competitions found"
    return comp_ctx


@when(parsers.parse('I request standings for "{competition}" season {season:d}'))
def get_standings_query(comp_ctx, competition, season):
    comp_ctx.result = get_competition_standings(competition=competition, season=season)


@then("I should receive a standings list")
def verify_standings_list(comp_ctx):
    assert isinstance(comp_ctx.result, list)
    assert len(comp_ctx.result) > 0


@then("each entry should have position, points, wins, draws, losses")
def verify_standings_fields(comp_ctx):
    for entry in comp_ctx.result:
        assert "position" in entry
        assert "pts" in entry
        assert "w" in entry
        assert "d" in entry
        assert "l" in entry
        assert "team" in entry


@then("the first-placed team should have the most points")
def verify_standings_order(comp_ctx):
    if len(comp_ctx.result) >= 2:
        assert comp_ctx.result[0]["pts"] >= comp_ctx.result[1]["pts"]


# ---------------------------------------------------------------------------
# Feature: Statistical Analysis
# ---------------------------------------------------------------------------


@given("the statistical data is available", target_fixture="stats_ctx")
def stats_data_available(stats_ctx):
    stats = get_statistics()
    assert stats["total_matches"] > 0, "No match statistics available"
    return stats_ctx


@when(parsers.parse('I request statistics for competition "{competition}"'))
def get_stats_query(stats_ctx, competition):
    stats_ctx.result = get_statistics(competition=competition)


@then("I should receive aggregate statistics")
def verify_stats_fields(stats_ctx):
    r = stats_ctx.result
    assert "total_matches" in r
    assert "avg_goals" in r
    assert "home_win_rate" in r
    assert "biggest_wins" in r


@then("average goals should be a positive number")
def verify_avg_goals(stats_ctx):
    assert stats_ctx.result["avg_goals"] > 0


@then("home win rate should be between 0 and 100")
def verify_home_win_rate(stats_ctx):
    assert 0 <= stats_ctx.result["home_win_rate"] <= 100


# ---------------------------------------------------------------------------
# Feature: Team Name Normalisation
# ---------------------------------------------------------------------------


@given("the team name normaliser is available", target_fixture="norm_ctx")
def normaliser_available(norm_ctx):
    return norm_ctx


@when(parsers.parse('I normalise the team name "{raw_name}"'))
def normalise_team_name(norm_ctx, raw_name):
    norm_ctx.result = normalize_team(raw_name)


@then(parsers.parse('the result should be "{expected}"'))
def verify_normalised_name(norm_ctx, expected):
    assert norm_ctx.result == expected, f"Expected '{expected}', got '{norm_ctx.result}'"


# ---------------------------------------------------------------------------
# Feature: Data Coverage
# ---------------------------------------------------------------------------


@given("all datasets are loaded", target_fixture="coverage_ctx")
def all_datasets_loaded(coverage_ctx):
    coverage_ctx.teams = list_teams()
    coverage_ctx.competitions = list_competitions()
    coverage_ctx.seasons = list_seasons()
    return coverage_ctx


@when("I query for available teams and competitions")
def query_coverage(coverage_ctx):
    pass


@then("I should find teams from all match datasets")
def verify_team_coverage(coverage_ctx):
    key_teams = ["Flamengo", "Palmeiras", "Corinthians", "Sao Paulo"]
    teams_lower = [t.lower() for t in coverage_ctx.teams]
    for team in key_teams:
        assert any(team.lower() in t for t in teams_lower), \
            f"Team '{team}' not found in dataset"


@then("I should find multiple competitions")
def verify_competition_coverage(coverage_ctx):
    assert len(coverage_ctx.competitions) >= 3, \
        f"Expected >= 3 competitions, got {coverage_ctx.competitions}"


@then("I should find multiple seasons")
def verify_season_coverage(coverage_ctx):
    assert len(coverage_ctx.seasons) >= 5, \
        f"Expected >= 5 seasons, got {coverage_ctx.seasons}"
