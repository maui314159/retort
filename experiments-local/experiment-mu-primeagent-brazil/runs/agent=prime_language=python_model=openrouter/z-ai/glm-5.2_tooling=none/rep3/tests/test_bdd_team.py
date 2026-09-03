"""
Context Block
=============

Module: tests.test_bdd_team
Purpose: BDD (Given-When-Then) scenarios for team queries.
"""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp.queries import SoccerQueries


class TestTeamQueriesBDD:
    """BDD scenarios for the Team Queries feature."""

    @pytest.mark.bdd
    def test_team_statistics_basic(self, queries: SoccerQueries):
        """
        Scenario: Get team statistics
          Given the match data is loaded
          When I request statistics for "Palmeiras"
          Then I should receive wins, losses, draws, and goals
        """
        # When
        result = queries.team_statistics("Palmeiras")

        # Then
        assert result["matches"] > 0
        assert result["wins"] + result["draws"] + result["losses"] == result["matches"]
        assert result["goals_for"] >= 0
        assert result["goals_against"] >= 0
        assert 0 <= result["win_rate"] <= 100

    @pytest.mark.bdd
    def test_team_statistics_by_season(self, queries: SoccerQueries):
        """
        Scenario: Get team statistics for a specific season
          Given the match data is loaded
          When I request statistics for "Palmeiras" in season 2019
          Then I should receive season-specific statistics
        """
        # When
        result = queries.team_statistics("Palmeiras", season=2019)

        # Then
        assert result["season"] == 2019
        assert result["matches"] > 0
        assert result["wins"] + result["draws"] + result["losses"] == result["matches"]

    @pytest.mark.bdd
    def test_corinthians_home_record_2022(self, queries: SoccerQueries):
        """
        Scenario: Corinthians home record in 2022
          Given the match data is loaded
          When I request home statistics for "Corinthians" in 2022
          Then I should receive home-only statistics
        """
        # When
        result = queries.team_statistics("Corinthians", season=2022, venue="home")

        # Then
        assert result["venue"] == "home"
        assert result["season"] == 2022
        assert result["matches"] > 0
        assert result["wins"] + result["draws"] + result["losses"] == result["matches"]

    @pytest.mark.bdd
    def test_team_info(self, queries: SoccerQueries):
        """
        Scenario: Get team information
          Given the match data is loaded
          When I request info for "Flamengo"
          Then I should receive team overview with competitions
        """
        # When
        result = queries.team_info("Flamengo")

        # Then
        assert result["team"] is not None
        assert result["total_matches"] > 0
        assert "competitions" in result
        assert "Brasileirao" in result["competitions"]

    @pytest.mark.bdd
    def test_compare_teams(self, queries: SoccerQueries):
        """
        Scenario: Compare two teams
          Given the match data is loaded
          When I compare "Palmeiras" and "Santos"
          Then I should receive both teams' info and head-to-head
        """
        # When
        result = queries.compare_teams("Palmeiras", "Santos")

        # Then
        assert "team1" in result
        assert "team2" in result
        assert "head_to_head" in result
        assert result["team1"]["team"] == "Palmeiras"
        assert result["team2"]["team"] == "Santos"

    @pytest.mark.bdd
    def test_best_home_record(self, queries: SoccerQueries):
        """
        Scenario: Which team has the best home record
          Given the match data is loaded
          When I request the best home records in Brasileirao
          Then I should receive a ranked list
        """
        # When
        result = queries.best_home_record(competition="Brasileirao")

        # Then
        assert len(result["rankings"]) > 0
        # Rankings should be sorted by win_rate descending
        rates = [r["win_rate"] for r in result["rankings"]]
        assert rates == sorted(rates, reverse=True)

    @pytest.mark.bdd
    def test_best_away_record(self, queries: SoccerQueries):
        """
        Scenario: Which team has the best away record
          Given the match data is loaded
          When I request the best away records in Brasileirao
          Then I should receive a ranked list
        """
        # When
        result = queries.best_away_record(competition="Brasileirao")

        # Then
        assert len(result["rankings"]) > 0

    @pytest.mark.bdd
    def test_team_name_variation_matching(self, queries: SoccerQueries):
        """
        Scenario: Team name variations are matched correctly
          Given the match data is loaded
          When I search for "Flamengo-RJ" and "Flamengo"
          Then both should return the same team
        """
        # When
        r1 = queries.team_info("Flamengo-RJ")
        r2 = queries.team_info("Flamengo")

        # Then
        assert r1["team_key"] == r2["team_key"]
        assert r1["team_key"] == "flamengo"
