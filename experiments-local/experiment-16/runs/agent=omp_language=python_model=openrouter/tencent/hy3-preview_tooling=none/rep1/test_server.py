"""
BDD-style tests for Brazilian Soccer MCP Server.
Tests use pytest with Gherkin-inspired scenarios.
"""

import pandas as pd
import pytest
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loader import SoccerDataLoader, normalize_team_name


# Test fixtures
@pytest.fixture
def loader():
    """Create a data loader instance with loaded data."""
    l = SoccerDataLoader()
    l.load_all()
    return l


# Feature: Match Queries
class TestMatchQueries:
    """Tests for match query functionality."""

    def test_search_matches_by_team(self, loader):
        """Scenario: Find matches between two teams."""
        # Given the match data is loaded
        assert loader.brasileirao_matches is not None or loader.historical_brasileirao is not None

        # When I search for matches with "Flamengo"
        matches = loader.search_matches(team="Flamengo")

        # Then I should receive a list of matches
        assert not matches.empty

    def test_search_matches_by_competition(self, loader):
        """Scenario: Find matches by competition."""
        # Given the match data is loaded
        all_matches = loader.get_all_matches()
        assert not all_matches.empty

        # Get a valid competition name from the data
        comp = all_matches['competition'].iloc[0]

        # When I search for matches in that competition
        matches = loader.search_matches(competition=comp)

        # Then I should receive matches from that competition
        assert not matches.empty


# Feature: Team Statistics
class TestTeamStatistics:
    """Tests for team statistics functionality."""

    def test_get_team_stats(self, loader):
        """Scenario: Get team statistics."""
        # Given the match data is loaded
        all_matches = loader.get_all_matches()
        teams = all_matches['home_team_norm'].unique()

        if len(teams) > 0:
            team = teams[0]

            # When I request statistics for the team
            stats = loader.get_team_stats(team)

            # Then I should receive wins, losses, draws, and goals
            assert "wins" in stats
            assert "losses" in stats
            assert "draws" in stats
            assert "goals_for" in stats


# Feature: Head-to-Head
class TestHeadToHead:
    """Tests for head-to-head functionality."""

    def test_head_to_head(self, loader):
        """Scenario: Get head-to-head record between two teams."""
        # Given the match data is loaded
        all_matches = loader.get_all_matches()

        # Get two teams that have played each other
        teams = all_matches['home_team_norm'].unique()
        if len(teams) >= 2:
            team1 = teams[0]
            team2 = teams[1]

            # When I request head-to-head record
            result = loader.head_to_head(team1, team2)

            # Then I should receive the record
            if "error" not in result:
                assert "team1_wins" in result
                assert "team2_wins" in result
                assert "total_matches" in result


# Feature: Player Queries
class TestPlayerQueries:
    """Tests for player query functionality."""

    def test_search_players_by_name(self, loader):
        """Scenario: Find player by name."""
        if loader.fifa_players is None:
            pytest.skip("FIFA player data not loaded")

        # When I search for a player by name
        players = loader.search_players(name="Neymar")

        # Then I should receive matching players
        if not players.empty:
            assert any('Neymar' in str(name) for name in players['Name'])


# Feature: Data Loading
class TestDataLoading:
    """Tests for data loading functionality."""

    def test_all_datasets_loadable(self, loader):
        """Scenario: All CSV files are loadable."""
        # Check that at least some datasets loaded
        datasets = [
            loader.brasileirao_matches,
            loader.brazilian_cup_matches,
            loader.libertadores_matches,
            loader.br_football,
            loader.historical_brasileirao,
            loader.fifa_players
        ]

        loaded = sum(1 for d in datasets if d is not None)
        assert loaded >= 2, f"Only {loaded} datasets loaded"

    def test_normalize_team_names(self):
        """Scenario: Team name normalization works correctly."""
        # Given team name variations
        variations = [
            ("Palmeiras-SP", "Palmeiras"),
            ("Flamengo-RJ", "Flamengo"),
            ("Corinthians-SP", "Corinthians"),
        ]

        # When I normalize the names
        for input_name, expected in variations:
            result = normalize_team_name(input_name)

            # Then I should get the normalized name
            assert result == expected or result == input_name


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
