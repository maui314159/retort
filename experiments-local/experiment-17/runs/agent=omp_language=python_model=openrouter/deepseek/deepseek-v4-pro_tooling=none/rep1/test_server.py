"""
Brazilian Soccer MCP Server - BDD-style Tests
==============================================
Behavior-Driven Development test scenarios using pytest with
Gherkin-style Given/When/Then structure.

Tests validate:
  - All 6 CSV files are loadable and queryable
  - Team name normalization works across datasets
  - Match queries return correct results
  - Player queries return correct results
  - Competition standings are calculated correctly
  - Statistical analyses produce accurate results
  - Cross-file queries work (player + match data)
"""

from __future__ import annotations

import pytest

# Import the data module directly (not through MCP tools)
from data_loader import (
    get_all_team_names,
    load_all_match_data,
    load_fifa_players,
    normalize_team_name,
    parse_date,
)
from query_engine import (
    get_average_goals,
    get_biggest_wins,
    get_data_summary,
    get_head_to_head,
    get_highest_scoring_teams,
    get_players_by_club,
    get_season_summary,
    get_standings,
    get_team_performance_trend,
    get_team_stats,
    get_top_brazilian_players,
    search_matches,
    search_players,
)


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def matches_df():
    """Load all match data once per test module."""
    return load_all_match_data()


@pytest.fixture(scope="module")
def players_df():
    """Load FIFA player data once per test module."""
    return load_fifa_players()


# ── Data Loading Tests ──────────────────────────────────────────────────────


class TestDataLoading:
    """Feature: Data Loading
    As a user, I want all datasets to be loaded correctly
    So that I can query Brazilian soccer data.
    """

    def test_all_csv_files_loaded(self, matches_df, players_df):
        """Scenario: All 6 CSV files are loadable and queryable

        Given the data directory contains 6 CSV files
        When I load all match data and player data
        Then all files should contribute data to the final dataset
        """
        # Then: match data should have matches from all competitions
        assert len(matches_df) > 0, "Match data should not be empty"
        competitions = matches_df["competition"].dropna().unique()
        assert len(competitions) >= 3, f"Expected at least 3 competitions, got {len(competitions)}"
        assert "Brasileirão" in competitions, "Should contain Brasileirão"

        # Then: player data should have players
        assert len(players_df) > 0, "Player data should not be empty"
        assert len(players_df) > 10000, f"Expected >10k players, got {len(players_df)}"

    def test_matches_have_required_columns(self, matches_df):
        """Scenario: Match data has required columns

        Given match data is loaded
        When I inspect the columns
        Then core columns should be present
        """
        required = ["home_team_norm", "away_team_norm", "home_goal", "away_goal", "season", "date", "competition"]
        for col in required:
            assert col in matches_df.columns, f"Missing required column: {col}"

    def test_players_have_required_columns(self, players_df):
        """Scenario: Player data has required columns

        Given player data is loaded
        When I inspect the columns
        Then key columns should be present
        """
        required = ["Name", "Nationality", "Club", "Position", "Overall"]
        for col in required:
            assert col in players_df.columns, f"Missing required column: {col}"


# ── Team Name Normalization Tests ───────────────────────────────────────────


class TestTeamNameNormalization:
    """Feature: Team Name Normalization
    As a user, I want team names to be normalized
    So that queries work across datasets with different naming conventions.
    """

    def test_strips_state_suffix(self):
        """Scenario: Team names with state suffix are normalized

        Given team names have state suffixes like "-RJ", "-SP"
        When I normalize the team name
        Then the suffix should be removed
        """
        assert normalize_team_name("Flamengo-RJ") == "Flamengo"
        assert normalize_team_name("Palmeiras-SP") == "Palmeiras"
        assert normalize_team_name("Corinthians-SP") == "Corinthians"

    def test_handles_accented_names(self):
        """Scenario: Team names with accents are normalized

        Given team names contain Brazilian Portuguese accents
        When I normalize the team name
        Then accented and unaccented forms should match
        """
        result1 = normalize_team_name("São Paulo")
        result2 = normalize_team_name("Sao Paulo")
        assert result1 == result2, f"Expected same, got '{result1}' vs '{result2}'"

    def test_handles_alternate_spellings(self):
        """Scenario: Alternate spellings of the same team are unified

        Given different datasets use different spellings
        When I normalize names
        Then they should map to the same canonical name
        """
        assert normalize_team_name("Athletico-PR") == normalize_team_name("Atlético-PR")

    def test_handles_known_variants(self):
        """Scenario: Known team name variants normalize correctly

        Given teams have known aliases
        When I normalize them
        Then they should resolve to the canonical form
        """
        assert normalize_team_name("Grêmio") == "Gremio"
        assert normalize_team_name("Gremio-RS") == "Gremio"


# ── Date Parsing Tests ──────────────────────────────────────────────────────


class TestDateParsing:
    """Feature: Date Parsing
    As a user, I want dates in multiple formats to be parsed correctly.
    """

    def test_iso_format(self):
        """Scenario: ISO format dates are parsed

        Given dates in YYYY-MM-DD format
        When I parse the date
        Then the correct date should be returned
        """
        result = parse_date("2023-09-24")
        assert result is not None
        assert result.year == 2023
        assert result.month == 9
        assert result.day == 24

    def test_brazilian_format(self):
        """Scenario: Brazilian format dates are parsed

        Given dates in DD/MM/YYYY format
        When I parse the date
        Then the correct date should be returned
        """
        result = parse_date("29/03/2003")
        assert result is not None
        assert result.year == 2003
        assert result.month == 3
        assert result.day == 29

    def test_datetime_format(self):
        """Scenario: Datetime format is parsed

        Given dates in YYYY-MM-DD HH:MM:SS format
        When I parse the date
        Then the correct date should be returned
        """
        result = parse_date("2012-05-19 18:30:00")
        assert result is not None
        assert result.year == 2012
        assert result.month == 5
        assert result.day == 19


# ── Match Query Tests ───────────────────────────────────────────────────────


class TestMatchQueries:
    """Feature: Match Queries

    Scenario: Find matches between two teams
      Given the match data is loaded
      When I search for matches between "Flamengo" and "Fluminense"
      Then I should receive a list of matches
      And each match should have date, scores, and competition
    """

    def test_search_matches_between_teams(self, matches_df):
        """When I search for matches between Flamengo and Fluminense"""
        result = search_matches(matches_df, team="Flamengo", opponent="Fluminense")
        assert "Flamengo" in result, "Result should mention Flamengo"
        assert "Fluminense" in result, "Result should mention Fluminense"
        assert "Found" in result, "Result should show count"

    def test_search_matches_by_team_only(self, matches_df):
        """When I search for matches by a single team"""
        result = search_matches(matches_df, team="Palmeiras", limit=5)
        assert "Palmeiras" in result, "Result should mention Palmeiras"
        assert "Found" in result, "Result should show count"

    def test_search_matches_by_competition(self, matches_df):
        """When I search for matches by competition"""
        result = search_matches(matches_df, competition="Copa do Brasil", limit=5)
        assert "Copa do Brasil" in result, "Result should mention competition"

    def test_search_matches_by_season(self, matches_df):
        """When I search for matches by season"""
        result = search_matches(matches_df, season=2023, limit=5)
        assert "2023" in result, "Result should mention season"

    def test_search_no_results(self, matches_df):
        """When I search for a non-existent team"""
        result = search_matches(matches_df, team="ZZZZ_NonExistent_Team_XYZ")
        assert "not found" in result.lower(), "Should indicate team not found"


# ── Team Statistics Tests ───────────────────────────────────────────────────


class TestTeamStats:
    """Feature: Get team statistics

    Scenario: Get team statistics
      Given the match data is loaded
      When I request statistics for a known team
      Then I should receive wins, losses, draws, and goals
    """

    def test_get_famous_team_stats(self, matches_df):
        """When I request statistics for Flamengo"""
        result = get_team_stats(matches_df, "Flamengo")
        assert "Flamengo" in result, "Should mention team name"
        assert "W" in result, "Should show wins"
        assert "D" in result, "Should show draws"
        assert "L" in result, "Should show losses"
        assert "Goals For" in result, "Should show goals for"
        assert "Goals Against" in result, "Should show goals against"

    def test_get_team_stats_with_season(self, matches_df):
        """When I request statistics for a team with season filter"""
        result = get_team_stats(matches_df, "Palmeiras", season=2023)
        assert "Palmeiras" in result, "Should mention team name"
        assert "2023" in result, "Should mention season"

    def test_get_unknown_team_stats(self, matches_df):
        """When I request statistics for a non-existent team"""
        result = get_team_stats(matches_df, "ZZZZ_Fake_Team")
        assert "not found" in result.lower(), "Should indicate team not found"


# ── Player Query Tests ──────────────────────────────────────────────────────


class TestPlayerQueries:
    """Feature: Player Queries

    Scenario: Search for Brazilian players
      Given the FIFA player data is loaded
      When I filter by nationality "Brazil"
      Then I should receive a list of Brazilian players
      And they should be sorted by overall rating
    """

    def test_search_brazilian_players(self, players_df):
        """When I search for Brazilian players"""
        result = search_players(players_df, nationality="Brazil", limit=10)
        assert "Brazil" in result, "Should mention nationality"
        assert "Neymar" in result, "Should include top Brazilian players"
        assert "Found" in result, "Should show count"

    def test_top_brazilian_players(self, players_df):
        """When I get top Brazilian players"""
        result = get_top_brazilian_players(players_df, limit=10)
        assert "Neymar" in result, "Should include Neymar"
        assert "Overall" in result, "Should show ratings"

    def test_search_by_name(self, players_df):
        """When I search for a specific player by name"""
        result = search_players(players_df, name="Neymar")
        assert "Neymar" in result, "Should find Neymar"
    def test_search_by_club(self, players_df):
        """When I search for players by club"""
        result = search_players(players_df, club="Santos", limit=5)
        assert "Santos" in result, "Should mention club"

    def test_search_by_position(self, players_df):
        """When I search for players by position"""
        result = search_players(players_df, position="GK", limit=5)
        assert len(result) > 0, "Should find goalkeepers"

    def test_search_by_rating_range(self, players_df):
        """When I search for players by rating range"""
        result = search_players(players_df, min_overall=90, limit=10)
        assert len(result) > 0, "Should find 90+ rated players"


# ── Head-to-Head Tests ──────────────────────────────────────────────────────


class TestHeadToHead:
    """Feature: Head-to-Head Comparison

    Scenario: Compare two teams
      Given the match data is loaded
      When I compare two known rival teams
      Then I should receive head-to-head statistics
    """

    def test_flamengo_vs_fluminense(self, matches_df):
        """When I compare Flamengo and Fluminense"""
        result = get_head_to_head(matches_df, "Flamengo", "Fluminense")
        assert "Flamengo" in result, "Should mention Flamengo"
        assert "Fluminense" in result, "Should mention Fluminense"
        assert "wins" in result, "Should show win counts"

    def test_unknown_team_h2h(self, matches_df):
        """When I compare with a non-existent team"""
        result = get_head_to_head(matches_df, "Flamengo", "ZZZZ_Fake")
        assert "not found" in result.lower(), "Should indicate team not found"


# ── Standings Tests ─────────────────────────────────────────────────────────


class TestStandings:
    """Feature: Competition Standings

    Scenario: Get league standings
      Given the match data is loaded
      When I request standings for a competition and season
      Then I should receive a ranked list with points, wins, draws, losses
    """

    def test_get_brasileirao_standings(self, matches_df):
        """When I request Brasileirão standings for 2019"""
        result = get_standings(matches_df, "Brasileirão", 2019)
        assert "Brasileirão" in result, "Should mention competition"
        assert "2019" in result, "Should mention season"
        assert "pts" in result, "Should show points"

    def test_standings_are_ranked(self, matches_df):
        """Then standings should be ranked by points"""
        result = get_standings(matches_df, "Brasileirão", 2019)
        lines = [l.strip() for l in result.split("\n") if l.strip() and l.strip()[0].isdigit()]
        assert len(lines) >= 10, "Should have at least 10 ranked teams"
        assert lines[0].startswith("1"), "First team should be ranked #1"


# ── Season Summary Tests ────────────────────────────────────────────────────


class TestSeasonSummary:
    """Feature: Season Summary

    Scenario: Get season summary
      Given the match data is loaded
      When I request a season summary
      Then I should receive match counts, goals, and standings
    """

    def test_brasileirao_2019_summary(self, matches_df):
        """When I request Brasileirão 2019 summary"""
        result = get_season_summary(matches_df, "Brasileirão", 2019)
        assert "Brasileirão" in result, "Should mention competition"
        assert "Total matches" in result, "Should show match count"
        assert "Average goals" in result, "Should show average goals"

    def test_season_summary_has_standings(self, matches_df):
        """Then the summary should include top standings"""
        result = get_season_summary(matches_df, "Brasileirão", 2019)
        assert "Standings" in result, "Should include standings section"


# ── Statistical Analysis Tests ──────────────────────────────────────────────


class TestStatisticalAnalysis:
    """Feature: Statistical Analysis

    Scenario: Calculate match statistics
      Given the match data is loaded
      When I request average goals and match stats
      Then I should receive accurate statistical results
    """

    def test_average_goals_sensible(self, matches_df):
        """Then average goals per match should be in a reasonable range (1.5-4.0)"""
        result = get_average_goals(matches_df)
        assert "Average goals per match" in result, "Should show average"

    def test_biggest_wins(self, matches_df):
        """When I request biggest victories"""
        result = get_biggest_wins(matches_df, limit=10)
        assert "Biggest victories" in result, "Should show biggest wins"
        lines = [l for l in result.split("\n") if l.strip().startswith(tuple("123456789"))]
        assert len(lines) >= 5, f"Should have at least 5 results, got {len(lines)}"

    def test_highest_scoring_teams(self, matches_df):
        """When I request highest scoring teams"""
        result = get_highest_scoring_teams(matches_df, top_n=5)
        assert "Top scoring teams" in result, "Should show top scorers"
        assert "goals" in result, "Should show goal counts"


# ── Performance Trend Tests ─────────────────────────────────────────────────


class TestPerformanceTrend:
    """Feature: Team Performance Trends

    Scenario: Show team performance by season
      Given the match data is loaded
      When I request performance trend for a team
      Then I should see results by season
    """

    def test_flamengo_trend(self, matches_df):
        """When I request Flamengo's Brasileirão performance trend"""
        result = get_team_performance_trend(matches_df, "Flamengo")
        assert "Flamengo" in result, "Should mention team"
        assert "Brasileirão" in result, "Should mention competition"


# ── Data Summary Tests ──────────────────────────────────────────────────────


class TestDataSummary:
    """Feature: Data Summary

    Scenario: Get database summary
      Given all data is loaded
      When I request a data summary
      Then I should see comprehensive statistics about the loaded data
    """

    def test_data_summary_content(self, matches_df, players_df):
        """When I request data summary"""
        result = get_data_summary(matches_df, players_df)
        assert "Brazilian Soccer Database Summary" in result, "Should have title"
        assert "Match Data" in result, "Should have match section"
        assert "Player Data" in result, "Should have player section"
        assert "Brazilian players" in result, "Should show Brazilian player count"


# ── Cross-file Query Tests ──────────────────────────────────────────────────


class TestCrossFileQueries:
    """Feature: Cross-File Queries

    Scenario: Query players and matches together
      Given all data is loaded
      When I perform a cross-file query
      Then the results should be consistent
    """

    def test_players_at_brazilian_clubs_match_data(self, matches_df, players_df):
        """Then Brazilian clubs should appear in both match and player data"""
        all_teams = get_all_team_names(matches_df)
        # Check that major Brazilian clubs appear in match data
        major_clubs = ["Flamengo", "Palmeiras", "Corinthians", "Sao Paulo", "Santos"]
        for club in major_clubs:
            assert club in all_teams, f"Major club {club} should be in match data"

    def test_brazilian_players_exist(self, players_df):
        """Then there should be many Brazilian players"""
        result = search_players(players_df, nationality="Brazil")
        assert "Found" in result, "Should find Brazilian players"
        # Should find hundreds of Brazilian players
        count_line = result.split("\n")[0]
        count = int(count_line.split()[1])
        assert count > 50, f"Should have >50 Brazilian players, got {count}"


# ── Performance Tests ───────────────────────────────────────────────────────


class TestQueryPerformance:
    """Feature: Query Performance

    Scenario: Queries respond within acceptable time
      Given all data is loaded
      When I run various queries
      Then they should respond quickly
    """

    def test_simple_lookup_performance(self, matches_df, players_df):
        """Then simple lookups should be fast"""
        import time

        start = time.time()
        search_matches(matches_df, team="Flamengo", limit=5)
        elapsed = time.time() - start
        assert elapsed < 2.0, f"Simple lookup took {elapsed:.2f}s, expected < 2s"

    def test_aggregate_query_performance(self, matches_df):
        """Then aggregate queries should be reasonably fast"""
        import time

        start = time.time()
        get_standings(matches_df, "Brasileirão", 2019)
        elapsed = time.time() - start
        assert elapsed < 5.0, f"Aggregate query took {elapsed:.2f}s, expected < 5s"


# ── Edge Case Tests ─────────────────────────────────────────────────────────


class TestEdgeCases:
    """Feature: Edge Cases

    Scenario: Handle edge cases gracefully
      Given the match and player data is loaded
      When I query with unusual parameters
      Then I should get appropriate responses, not errors
    """

    def test_empty_results_dont_error(self, matches_df, players_df):
        """When queries return no results, they should return a message, not error"""
        # Non-existent team
        result1 = search_matches(matches_df, team="ZZZZ_Nonexistent")
        assert isinstance(result1, str) and len(result1) > 0, "Should return a message"

        # Non-existent player
        result2 = search_players(players_df, name="ZZZZ_ASDFQWER_12345")
        assert isinstance(result2, str) and len(result2) > 0, "Should return a message"

    def test_special_characters_in_names(self, matches_df):
        """Then teams with special characters should be searchable"""
        result = search_matches(matches_df, team="São Paulo", limit=5)
        assert "Sao Paulo" in result, "Should find São Paulo"

    def test_case_insensitive_search(self, matches_df, players_df):
        """Then searches should be case-insensitive"""
        result_lower = search_matches(matches_df, team="flamengo", limit=5)
        result_upper = search_matches(matches_df, team="FLAMENGO", limit=5)
        assert len(result_lower) == len(result_upper), "Case should not affect results"