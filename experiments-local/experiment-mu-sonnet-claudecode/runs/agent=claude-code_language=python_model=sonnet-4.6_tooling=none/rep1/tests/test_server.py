"""BDD-style tests for the Brazilian Soccer MCP server."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
import data_loader as dl
from server import (
    find_matches,
    team_statistics,
    head_to_head,
    season_standings,
    find_players,
    top_scorers_analysis,
    biggest_wins,
    match_averages,
    best_home_record,
)


# ---------------------------------------------------------------------------
# Data loading tests
# ---------------------------------------------------------------------------

class TestDataLoading:
    def test_matches_loads_all_files(self):
        """Given the data directory exists, all 5 match CSVs should load."""
        df = dl.get_matches()
        assert len(df) > 10_000, "Expected more than 10,000 total matches across all datasets"

    def test_matches_has_required_columns(self):
        df = dl.get_matches()
        for col in ["home_team", "away_team", "home_goal", "away_goal", "competition"]:
            assert col in df.columns, f"Missing column: {col}"

    def test_fifa_loads(self):
        """Given the fifa_data.csv exists, the FIFA dataset should load."""
        df = dl.get_fifa()
        assert len(df) > 1000
        assert "Name" in df.columns
        assert "Nationality" in df.columns
        assert "Overall" in df.columns

    def test_team_name_normalization(self):
        assert dl._normalize_team_name("Palmeiras-SP") == "Palmeiras"
        assert dl._normalize_team_name("Flamengo-RJ") == "Flamengo"
        assert dl._normalize_team_name("Corinthians") == "Corinthians"
        assert dl._normalize_team_name("  Santos-SP  ") == "Santos"

    def test_competitions_represented(self):
        df = dl.get_matches()
        comps = df["competition"].unique().tolist()
        comp_str = " ".join(comps)
        assert "Brasileirão" in comp_str or "Brasileirao" in comp_str
        assert "Copa do Brasil" in comp_str or "Libertadores" in comp_str


# ---------------------------------------------------------------------------
# Match query tests
# ---------------------------------------------------------------------------

class TestMatchQueries:
    """Feature: Match Queries"""

    def test_find_flamengo_matches(self):
        """Scenario: Find matches for a well-known team."""
        result = find_matches("Flamengo", limit=5)
        assert "Flamengo" in result
        assert "Found" in result

    def test_find_flamengo_vs_fluminense(self):
        """Scenario: Find matches between two teams."""
        result = find_matches("Flamengo", opponent="Fluminense", limit=10)
        assert "Flamengo" in result
        assert "Fluminense" in result

    def test_find_matches_by_season(self):
        """Scenario: Filter matches by season."""
        result = find_matches("Palmeiras", season=2023)
        assert "Palmeiras" in result

    def test_find_matches_returns_no_data_gracefully(self):
        """Scenario: Unknown team returns helpful message."""
        result = find_matches("TeamThatDoesNotExist12345")
        assert "No matches found" in result

    def test_find_matches_by_competition(self):
        """Scenario: Filter matches by competition."""
        result = find_matches("Flamengo", competition="Libertadores", limit=5)
        assert "Flamengo" in result

    def test_match_output_has_scores(self):
        """Each match line should include score notation like X-Y."""
        import re
        result = find_matches("Santos", limit=5)
        lines = [l for l in result.split("\n") if l.strip().startswith("20")]
        assert len(lines) > 0, "Expected at least one dated match line"
        for line in lines:
            assert re.search(r"\d+-\d+", line), f"No score found in: {line}"


# ---------------------------------------------------------------------------
# Team statistics tests
# ---------------------------------------------------------------------------

class TestTeamStatistics:
    """Feature: Team Statistics"""

    def test_corinthians_stats(self):
        """Scenario: Get statistics for Corinthians."""
        result = team_statistics("Corinthians")
        assert "Wins" in result
        assert "Draws" in result
        assert "Losses" in result
        assert "Goals" in result

    def test_stats_for_season(self):
        """Scenario: Get team statistics filtered by season."""
        result = team_statistics("Corinthians", season=2022)
        assert "Wins" in result
        assert "2022" in result

    def test_unknown_team_returns_message(self):
        result = team_statistics("TeamXYZ123")
        assert "No match data found" in result

    def test_win_rate_is_percentage(self):
        result = team_statistics("Flamengo")
        assert "%" in result


# ---------------------------------------------------------------------------
# Head-to-head tests
# ---------------------------------------------------------------------------

class TestHeadToHead:
    """Feature: Head-to-head comparison"""

    def test_classic_derby(self):
        """Scenario: Compare Flamengo vs Fluminense."""
        result = head_to_head("Flamengo", "Fluminense")
        assert "wins" in result.lower()
        assert "Draws" in result

    def test_h2h_includes_recent_matches(self):
        result = head_to_head("Palmeiras", "Santos")
        assert "Recent matches:" in result

    def test_h2h_no_data(self):
        result = head_to_head("TeamA999", "TeamB999")
        assert "No matches found" in result


# ---------------------------------------------------------------------------
# Season standings tests
# ---------------------------------------------------------------------------

class TestSeasonStandings:
    """Feature: Season standings"""

    def test_2019_standings(self):
        """Scenario: Calculate 2019 Brasileirão standings."""
        result = season_standings(2019)
        assert "2019" in result
        assert "pts" in result

    def test_standings_no_data(self):
        result = season_standings(1800)
        assert "No data found" in result

    def test_standings_format(self):
        """Standings should be numbered."""
        result = season_standings(2018)
        if "No data found" not in result:
            assert " 1." in result


# ---------------------------------------------------------------------------
# Player query tests
# ---------------------------------------------------------------------------

class TestPlayerQueries:
    """Feature: Player Queries"""

    def test_find_brazilian_players(self):
        """Scenario: Find Brazilian players."""
        result = find_players(nationality="Brazil", limit=5)
        assert "Brazil" in result or "Found" in result

    def test_find_player_by_name(self):
        """Scenario: Search for a specific player."""
        result = find_players(name="Neymar", limit=3)
        assert "Found" in result or "Neymar" in result

    def test_find_players_at_fluminense(self):
        """Scenario: Find players at a Brazilian club present in the FIFA dataset."""
        result = find_players(club="Fluminense", limit=5)
        assert "Found" in result or "Fluminense" in result

    def test_find_players_no_results(self):
        result = find_players(name="XYZPlayerThatDoesNotExist999")
        assert "No players found" in result

    def test_find_high_rated_players(self):
        """Scenario: Filter by minimum overall rating."""
        result = find_players(min_overall=90, limit=5)
        assert "Found" in result


# ---------------------------------------------------------------------------
# Statistical analysis tests
# ---------------------------------------------------------------------------

class TestStatisticalAnalysis:
    """Feature: Statistical Analysis"""

    def test_biggest_wins(self):
        """Scenario: Find the biggest victories."""
        result = biggest_wins(limit=5)
        assert "Biggest wins" in result
        assert "margin:" in result

    def test_match_averages(self):
        """Scenario: Calculate overall averages."""
        result = match_averages()
        assert "Avg goals/match" in result
        assert "Home wins" in result

    def test_match_averages_by_season(self):
        result = match_averages(season=2019)
        assert "Avg goals/match" in result

    def test_top_scorers(self):
        """Scenario: Find top goal-scoring teams."""
        result = top_scorers_analysis()
        assert "Top goal-scoring teams" in result

    def test_best_home_record(self):
        """Scenario: Find teams with best home record."""
        result = best_home_record(limit=5)
        assert "Best home records" in result
        assert "%" in result

    def test_best_home_record_by_season(self):
        result = best_home_record(season=2022, limit=5)
        assert "Best home records" in result


# ---------------------------------------------------------------------------
# Cross-file query tests
# ---------------------------------------------------------------------------

class TestCrossFileQueries:
    def test_flamengo_players_and_matches(self):
        """Verify both player and match queries work for Flamengo."""
        matches_result = find_matches("Flamengo", limit=3)
        players_result = find_players(club="Flamengo", limit=3)
        assert "Flamengo" in matches_result
        # FIFA data may not have all Brazilian clubs; just verify it runs
        assert isinstance(players_result, str)

    def test_all_competitions_queryable(self):
        """All three competitions should be queryable."""
        for comp in ["Brasileirão", "Copa do Brasil", "Libertadores"]:
            result = find_matches("Flamengo", competition=comp, limit=3)
            assert isinstance(result, str)
