"""
Context Block
=============

Module: tests.test_bdd_statistics
Purpose: BDD (Given-When-Then) scenarios for statistical analysis
         queries.
"""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp.queries import SoccerQueries


class TestStatisticsBDD:
    """BDD scenarios for the Statistical Analysis feature."""

    @pytest.mark.bdd
    def test_average_goals_brasileirao(self, queries: SoccerQueries):
        """
        Scenario: Average goals per match in the Brasileirao
          Given the match data is loaded
          When I request average goals for Brasileirao
          Then I should receive a positive average
        """
        # When
        result = queries.average_goals("Brasileirao")

        # Then
        assert result["avg_goals_per_match"] > 0
        assert result["total_matches"] > 0
        assert result["home_win_rate"] > 0

    @pytest.mark.bdd
    def test_biggest_wins(self, queries: SoccerQueries):
        """
        Scenario: Show the biggest wins in the dataset
          Given the match data is loaded
          When I request the biggest wins in Brasileirao
          Then I should receive a list sorted by margin
        """
        # When
        result = queries.biggest_wins("Brasileirao", limit=10)

        # Then
        assert len(result["biggest_wins"]) > 0
        margins = [w["margin"] for w in result["biggest_wins"]]
        assert margins == sorted(margins, reverse=True)
        # The biggest win should have a positive margin
        assert result["biggest_wins"][0]["margin"] > 0

    @pytest.mark.bdd
    def test_biggest_wins_all_competitions(self, queries: SoccerQueries):
        """
        Scenario: Biggest wins across all competitions
          Given the match data is loaded
          When I request the biggest wins with no competition filter
          Then I should receive wins from multiple competitions
        """
        # When
        result = queries.biggest_wins(limit=20)

        # Then
        assert len(result["biggest_wins"]) > 0
        competitions = set(w["competition"] for w in result["biggest_wins"])
        assert len(competitions) >= 1

    @pytest.mark.bdd
    def test_home_vs_away(self, queries: SoccerQueries):
        """
        Scenario: Home vs away performance
          Given the match data is loaded
          When I request home vs away stats for Brasileirao
          Then I should receive home and away win rates
        """
        # When
        result = queries.home_vs_away("Brasileirao")

        # Then
        assert result["home_win_rate"] > 0
        assert result["away_win_rate"] > 0
        # Home win rate typically exceeds away win rate
        assert result["home_win_rate"] >= result["away_win_rate"]

    @pytest.mark.bdd
    def test_biggest_wins_have_scores(self, queries: SoccerQueries):
        """
        Scenario: Biggest wins include score information
          Given the match data is loaded
          When I request the biggest wins
          Then each result should have winner, loser, and score
        """
        # When
        result = queries.biggest_wins(limit=5)

        # Then
        for w in result["biggest_wins"]:
            assert "winner" in w
            assert "loser" in w
            assert "score" in w
            assert "date" in w

    @pytest.mark.bdd
    def test_average_goals_by_season(self, queries: SoccerQueries):
        """
        Scenario: Average goals for a specific season
          Given the match data is loaded
          When I request average goals for Brasileirao 2019
          Then I should receive season-specific statistics
        """
        # When
        result = queries.average_goals("Brasileirao", season=2019)

        # Then
        assert result["avg_goals_per_match"] > 0
        assert result["season"] == 2019

    @pytest.mark.bdd
    def test_team_list(self, queries: SoccerQueries):
        """
        Scenario: List all teams
          Given the match data is loaded
          When I request the team list
          Then I should receive a list of teams
        """
        # When
        result = queries.team_list(limit=50)

        # Then
        assert result["count"] > 0
        assert result["total_found"] > 0

    @pytest.mark.bdd
    def test_search_all(self, queries: SoccerQueries):
        """
        Scenario: Cross-entity search
          Given the match data is loaded
          When I search for "Flamengo"
          Then I should receive matching teams, players, and possibly a competition
        """
        # When
        result = queries.search_all("Flamengo")

        # Then
        assert "teams" in result
        assert "players" in result
        assert result["teams"] is not None
