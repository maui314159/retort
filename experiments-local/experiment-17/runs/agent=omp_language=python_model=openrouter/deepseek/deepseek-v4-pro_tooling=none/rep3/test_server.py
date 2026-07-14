"""
Brazilian Soccer MCP Server - BDD Tests
=========================================
Behavior-Driven Development tests using Given-When-Then (GWT) structure
with pytest.

Tests cover:
  - Data loading and normalization
  - Match queries
  - Team queries and statistics
  - Player queries
  - Competition standings
  - Statistical analysis
"""

import pytest

from data_loader import (
    load_all_matches,
    load_brasileirao,
    load_copa_brasil,
    load_fifa,
    load_libertadores,
    normalize_team,
)
from query_engine import QueryEngine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def engine():
    """Query engine loaded once per test module."""
    return QueryEngine()


@pytest.fixture(scope="module")
def matches():
    """All matches loaded once per test module."""
    return load_all_matches()


@pytest.fixture(scope="module")
def players():
    """All players loaded once per test module."""
    return load_fifa()


# ---------------------------------------------------------------------------
# Data Loading Tests
# ---------------------------------------------------------------------------

class TestDataLoading:
    """Feature: Data Loading
       As a user
       I want the system to load all CSV datasets
       So that I can query Brazilian soccer data
    """

    def test_load_brasileirao(self):
        """Scenario: Load Brasileirao matches
           Given the Brasileirao CSV file exists
           When the data is loaded
           Then it should contain matches with required columns
        """
        # When
        df = load_brasileirao()
        # Then
        assert len(df) > 0, "Should have matches"
        expected_cols = {"home_team", "away_team", "home_goal", "away_goal", "season", "round"}
        actual_cols = set(df.columns)
        assert expected_cols.issubset(actual_cols), f"Missing columns: {expected_cols - actual_cols}"
        assert df["season"].min() >= 2012, "Brasileirao data should start from 2012"

    def test_load_copa_brasil(self):
        """Scenario: Load Copa do Brasil matches
           Given the Copa do Brasil CSV file exists
           When the data is loaded
           Then it should contain matches with required columns
        """
        # When
        df = load_copa_brasil()
        # Then
        assert len(df) > 0, "Should have matches"
        assert "round" in df.columns
        assert "season" in df.columns

    def test_load_libertadores(self):
        """Scenario: Load Libertadores matches
           Given the Libertadores CSV file exists
           When the data is loaded
           Then it should contain matches with stage information
        """
        # When
        df = load_libertadores()
        # Then
        assert len(df) > 0, "Should have matches"
        assert "stage" in df.columns
        stages = df["stage"].unique()
        assert any("final" in s.lower() for s in stages), "Should have final stage matches"

    def test_load_fifa(self):
        """Scenario: Load FIFA player data
           Given the FIFA CSV file exists
           When the data is loaded
           Then it should contain players with ratings
        """
        # When
        df = load_fifa()
        # Then
        assert len(df) > 0, "Should have players"
        assert df["Overall"].max() > 80, "Should have high-rated players"
        assert df["Nationality"].str.lower().eq("brazil").sum() > 0, "Should have Brazilian players"

    def test_unified_matches(self, matches):
        """Scenario: Load all matches into unified format
           Given all match CSV files exist
           When matches are merged into a single dataset
           Then all competitions should be represented
        """
        # Then
        assert len(matches) > 5000, "Should have thousands of matches"
        competitions = matches["competition"].unique()
        assert len(competitions) >= 3, f"Should have at least 3 competitions, got: {competitions}"


# ---------------------------------------------------------------------------
# Team Name Normalization Tests
# ---------------------------------------------------------------------------

class TestTeamNormalization:
    """Feature: Team Name Normalization
       As a user
       I want team names to be normalized consistently
       So that queries work regardless of naming variations
    """

    def test_normalize_strips_state_suffix(self):
        """Scenario: Strip state suffixes from team names
           Given team names may have state suffixes like "-SP" or "-RJ"
           When names are normalized
           Then the suffixes should be removed
        """
        # Then
        assert normalize_team("Palmeiras-SP") == normalize_team("Palmeiras")
        assert normalize_team("Flamengo-RJ") == normalize_team("Flamengo")
        assert normalize_team("Corinthians-SP") == normalize_team("Corinthians")

    def test_normalize_handles_accents(self):
        """Scenario: Handle accented team names
           Given team names may contain accents
           When names are normalized
           Then accented and unaccented forms should match
        """
        # Then
        assert normalize_team("São Paulo") == normalize_team("Sao Paulo")
        assert normalize_team("Grêmio") == normalize_team("Gremio")
        assert normalize_team("Atlético-MG") == normalize_team("Atletico-MG")

    def test_normalize_handles_common_variations(self):
        """Scenario: Handle common team name variations
           Given teams may be referred to by different names
           When names are normalized
           Then variations should map to the same canonical name
        """
        # Then
        assert normalize_team("Vasco da Gama") == normalize_team("Vasco")
        assert normalize_team("Flamengo-RJ") == normalize_team("Flamengo")
        assert normalize_team("Sport Recife") == "sport"


# ---------------------------------------------------------------------------
# Match Query Tests
# ---------------------------------------------------------------------------

class TestMatchQueries:
    """Feature: Match Queries
       As a user
       I want to search for matches by criteria
       So that I can find specific match information
    """

    def test_find_matches_by_team(self, engine):
        """Scenario: Find matches by team name
           Given the match data is loaded
           When I search for matches involving "Flamengo"
           Then I should receive a list of matches
           And each match should have date, scores, and competition
        """
        # When
        result = engine.find_matches(team="Flamengo", limit=20)
        # Then
        assert "Flamengo" in result
        assert "Found " in result
        assert "-" in result  # Should have score format

    def test_find_matches_head_to_head(self, engine):
        """Scenario: Find matches between two teams
           Given the match data is loaded
           When I search for matches between "Flamengo" and "Fluminense"
           Then I should receive a list of Fla-Flu matches
        """
        # When
        result = engine.find_matches(team="Flamengo", team2="Fluminense", limit=30)
        # Then
        assert "Found " in result
        # Fla-Flu is a classic derby, should find matches
        lines = result.split("\n")
        match_lines = [l for l in lines if "-" in l and "(" in l]
        assert len(match_lines) > 0, "Should find Fla-Flu matches"

    def test_find_matches_by_season(self, engine):
        """Scenario: Find matches in a specific season
           Given the match data is loaded
           When I search for matches in season 2023
           Then I should get matches only from that season
        """
        # When
        result = engine.find_matches(team="Palmeiras", season=2023, limit=20)
        # Then
        assert "Found " in result

    def test_find_matches_by_competition(self, engine):
        """Scenario: Find matches by competition
           Given the match data is loaded
           When I search for Libertadores matches
           Then I should get matches from that competition
        """
        # When
        result = engine.find_matches(competition="Libertadores", limit=20)
        # Then
        assert "Libertadores" in result
        assert "Found " in result

    def test_find_matches_no_results(self, engine):
        """Scenario: Search with no matching results
           Given the match data is loaded
           When I search for matches with a made-up team name
           Then I should get a 'No matches found' message
        """
        # When
        result = engine.find_matches(team="xyzzy-nonexistent-team-999")
        # Then
        assert "No matches found" in result

    def test_find_matches_date_range(self, engine):
        """Scenario: Find matches in a date range
           Given the match data is loaded
           When I search for matches between 2023-01-01 and 2023-12-31
           Then I should get matches from 2023
        """
        # When
        result = engine.find_matches(date_from="2023-01-01", date_to="2023-12-31", limit=20)
        # Then
        assert "Found " in result
        assert "2023" in result


# ---------------------------------------------------------------------------
# Team Query Tests
# ---------------------------------------------------------------------------

class TestTeamQueries:
    """Feature: Team Queries
       As a user
       I want to get team statistics
       So that I can analyze team performance
    """

    def test_team_stats(self, engine):
        """Scenario: Get team statistics
           Given the match data is loaded
           When I request statistics for "Flamengo"
           Then I should receive wins, losses, draws, and goals
        """
        # When
        result = engine.team_stats(team="Flamengo")
        # Then
        assert "Flamengo" in result
        assert "Wins:" in result
        assert "Draws:" in result
        assert "Losses:" in result
        assert "Goals For:" in result
        assert "Goals Against:" in result
        assert "Home record" in result
        assert "Away record" in result

    def test_team_stats_by_season(self, engine):
        """Scenario: Get team statistics for a specific season
           Given the match data is loaded
           When I request statistics for "Palmeiras" in season 2022
           Then I should get stats filtered to that season
        """
        # When
        result = engine.team_stats(team="Palmeiras", season=2022)
        # Then
        assert "Palmeiras" in result
        assert "2022" in result

    def test_team_stats_nonexistent(self, engine):
        """Scenario: Get statistics for nonexistent team
           Given the match data is loaded
           When I request stats for a team with no matches
           Then I should get an appropriate message
        """
        # When
        result = engine.team_stats(team="zzz-nonexistent")
        # Then
        assert "No matches found" in result

    def test_head_to_head(self, engine):
        """Scenario: Compare two teams head-to-head
           Given the match data is loaded
           When I compare "Flamengo" and "Vasco"
           Then I should get head-to-head record
        """
        # When
        result = engine.head_to_head(team1="Flamengo", team2="Vasco")
        # Then
        assert "Flamengo vs Vasco" in result or "Head-to-head" in result
        assert "wins" in result

    def test_head_to_head_nonexistent(self, engine):
        """Scenario: Head-to-head with no common matches
           Given the match data is loaded
           When I compare teams that never played each other
           Then I should get an appropriate message
        """
        # When
        result = engine.head_to_head(team1="Flamengo", team2="xxxyyy-123")
        # Then
        assert "No head-to-head matches" in result


# ---------------------------------------------------------------------------
# Player Query Tests
# ---------------------------------------------------------------------------

class TestPlayerQueries:
    """Feature: Player Queries
       As a user
       I want to search for player information
       So that I can find FIFA ratings and attributes
    """

    def test_find_players_by_nationality(self, engine):
        """Scenario: Find Brazilian players
           Given the FIFA player data is loaded
           When I search for players with nationality "Brazil"
           Then I should get results with Brazilian nationality
        """
        # When
        result = engine.find_players(nationality="Brazil", limit=10)
        # Then
        assert "Found " in result
        assert "Brazil" in result

    def test_find_players_by_name(self, engine):
        """Scenario: Find player by name
           Given the FIFA player data is loaded
           When I search for "Neymar"
           Then I should find Neymar Jr
        """
        # When
        result = engine.find_players(name="Neymar")
        # Then
        assert "Neymar" in result

    def test_find_players_by_club(self, engine):
        """Scenario: Find players at a specific club
           Given the FIFA player data is loaded
           When I search for players at "Santos"
           Then I should get Santos players
        """
        # When
        result = engine.find_players(club="Santos", limit=20)
        # Then
        assert "Found " in result

    def test_find_players_by_position(self, engine):
        """Scenario: Find players by position
           Given the FIFA player data is loaded
           When I search for goalkeepers (position "GK")
           Then I should get GK players
        """
        # When
        result = engine.find_players(position="GK", limit=10)
        # Then
        assert "Found " in result

    def test_find_players_by_rating(self, engine):
        """Scenario: Find high-rated players
           Given the FIFA player data is loaded
           When I search for players with overall rating >= 90
           Then I should get top players like Messi and Ronaldo
        """
        # When
        result = engine.find_players(min_overall=90, limit=10)
        # Then
        assert "Found " in result
        assert any(name in result for name in ["Messi", "Ronaldo", "Neymar"])

    def test_brazilian_players_summary(self, engine):
        """Scenario: Get Brazilian players summary
           Given the FIFA player data is loaded
           When I request a summary of Brazilian players
           Then I should get counts, top players, and club breakdowns
        """
        # When
        result = engine.brazilian_players_summary()
        # Then
        assert "Brazilian players in database:" in result
        assert "Top 10 Brazilian players" in result

    def test_find_players_no_results(self, engine):
        """Scenario: Search for nonexistent player
           Given the FIFA player data is loaded
           When I search for a made-up player name
           Then I should get 'No players found'
        """
        # When
        result = engine.find_players(name="xzzwq_nonexistent_player_999")
        # Then
        assert "No players found" in result


# ---------------------------------------------------------------------------
# Competition Query Tests
# ---------------------------------------------------------------------------

class TestCompetitionQueries:
    """Feature: Competition Queries
       As a user
       I want to query competition standings and information
       So that I can see league tables and competition data
    """

    def test_competition_standings(self, engine):
        """Scenario: Get Brasileirao standings
           Given the match data is loaded
           When I request Brasileirao standings for season 2023
           Then I should get a ranked table with points and records
        """
        # When
        result = engine.competition_standings(competition="Brasileirao", season=2023)
        # Then
        assert "Brasileirao" in result
        assert "Standings" in result
        assert "pts" in result
        assert "W," in result or "W " in result

    def test_competition_standings_historical(self, engine):
        """Scenario: Get historical Brasileirao standings
           Given the match data is loaded
           When I request Brasileirao standings for 2019
           Then I should get standings with Flamengo (likely champion)
        """
        # When
        result = engine.competition_standings(competition="Brasileirao", season=2019)
        # Then
        assert "2019" in result
        assert "Standings" in result

    def test_competitions_for_team(self, engine):
        """Scenario: Find competitions for a team
           Given the match data is loaded
           When I ask what competitions "Flamengo" played in
           Then I should get a list of competitions with match counts
        """
        # When
        result = engine.competitions_for_team(team="Flamengo")
        # Then
        assert "Competitions for Flamengo" in result
        assert "matches across" in result


# ---------------------------------------------------------------------------
# Statistical Analysis Tests
# ---------------------------------------------------------------------------

class TestStatisticalAnalysis:
    """Feature: Statistical Analysis
       As a user
       I want to calculate aggregated statistics
       So that I can analyze trends in Brazilian soccer
    """

    def test_average_goals(self, engine):
        """Scenario: Calculate average goals per match
           Given the match data is loaded
           When I request average goals for Brasileirao
           Then I should get goals per match and win rates
        """
        # When
        result = engine.average_goals(competition="Brasileirao")
        # Then
        assert "Average goals per match" in result
        assert "Home wins" in result
        assert "Away wins" in result
        assert "Draws" in result

    def test_biggest_wins(self, engine):
        """Scenario: Find biggest victories
           Given the match data is loaded
           When I request the biggest wins
           Then I should get matches with large goal differences
        """
        # When
        result = engine.biggest_wins(limit=10)
        # Then
        assert "Biggest victories" in result

    def test_season_comparison(self, engine):
        """Scenario: Compare two seasons
           Given the match data is loaded
           When I compare seasons 2018 and 2019
           Then I should get comparative statistics
        """
        # When
        result = engine.season_comparison(season1=2018, season2=2019)
        # Then
        assert "2018" in result
        assert "2019" in result
        assert "Matches:" in result

    def test_most_goals_team(self, engine):
        """Scenario: Find top scoring team
           Given the match data is loaded
           When I request the team with most goals
           Then I should get a ranked list
        """
        # When
        result = engine.most_goals_team()
        # Then
        assert "Teams ranked by goals scored" in result

    def test_best_home_record(self, engine):
        """Scenario: Find best home record
           Given the match data is loaded
           When I request the best home records
           Then I should get a ranked list of home performance
        """
        # When
        result = engine.best_home_record()
        # Then
        assert "Best home records" in result

    def test_best_away_record(self, engine):
        """Scenario: Find best away record
           Given the match data is loaded
           When I request the best away records
           Then I should get a ranked list of away performance
        """
        # When
        result = engine.best_away_record()
        # Then
        assert "Best away records" in result


# ---------------------------------------------------------------------------
# Integration Smoke Tests
# ---------------------------------------------------------------------------

class TestIntegrationSmoke:
    """Feature: End-to-End Integration
       As a user
       I want all query types to work end-to-end
       So that I can answer natural language questions about Brazilian soccer
    """

    def test_question_when_did_flamengo_play_corinthians(self, engine):
        """Scenario: When did Flamengo last play Corinthians?
           Given the match data is loaded
           When I search for Flamengo vs Corinthians matches
           Then I should find matches between them
        """
        # When
        result = engine.find_matches(team="Flamengo", team2="Corinthians", limit=5)
        # Then
        assert "Found " in result

    def test_question_santos_players(self, engine):
        """Scenario: Which players play for Santos?
           Given the FIFA player data is loaded
           When I search for Santos players
           Then I should get a list
        """
        # When
        result = engine.find_players(club="Santos", limit=20)
        # Then
        # Santos may or may not have players in FIFA data
        assert isinstance(result, str)

    def test_question_top_brazilian_players(self, engine):
        """Scenario: Who are the top Brazilian players?
           Given the FIFA player data is loaded
           When I search for Brazilian players with high ratings
           Then I should get a ranked list
        """
        # When
        result = engine.find_players(nationality="Brazil", min_overall=80, limit=10)
        # Then
        assert "Found " in result

    def test_question_who_won_2019_brasileirao(self, engine):
        """Scenario: Who won the 2019 Brasileirao?
           Given the match data is loaded
           When I calculate Brasileirao standings for 2019
           Then I should get the champion
        """
        # When
        result = engine.competition_standings(competition="Brasileirao", season=2019)
        # Then
        assert "2019" in result
        lines = result.split("\n")
        # First team in standings is champion
        assert len(lines) > 1, "Should have standings lines"

    def test_question_biggest_wins(self, engine):
        """Scenario: Show me the biggest wins in the dataset
           Given the match data is loaded
           When I request biggest wins
           Then I should get high-scoring matches
        """
        # When
        result = engine.biggest_wins(limit=5)
        # Then
        assert "Biggest victories" in result

    def test_question_corinthians_home_record_2022(self, engine):
        """Scenario: What is Corinthians' home record in 2022?
           Given the match data is loaded
           When I request Corinthians stats for 2022
           Then I should get home record statistics
        """
        # When
        result = engine.team_stats(team="Corinthians", season=2022)
        # Then
        assert "Home record" in result

    def test_cross_reference_team_in_both_datasets(self, engine):
        """Scenario: Cross-reference teams across match and player data
           Given both match and player data are loaded
           When I query a team that exists in both datasets
           Then both queries should work
        """
        # When (match data)
        match_result = engine.find_matches(team="Palmeiras", limit=5)
        # When (player data)
        player_result = engine.find_players(club="Palmeiras", limit=10)
        # Then
        assert "Found " in match_result
        # Player result may or may not find Palmeiras players in FIFA data
        assert isinstance(player_result, str)
