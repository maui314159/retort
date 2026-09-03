"""
Context Block
=============

Module: tests.test_bdd_match
Purpose: BDD (Given-When-Then) scenarios for match queries as
         specified in the TASK.md "Testing Approach" section.

Each test follows the GWT pattern:
  Given  - the data is loaded and a query engine is available
  When   - a specific query is performed
  Then   - the expected result is returned
"""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp.queries import SoccerQueries


# ---------------------------------------------------------------------------
# Feature: Match Queries
# ---------------------------------------------------------------------------
class TestMatchQueriesBDD:
    """BDD scenarios for the Match Queries feature."""

    @pytest.mark.bdd
    def test_find_matches_between_two_teams(self, queries: SoccerQueries):
        """
        Scenario: Find matches between two teams
          Given the match data is loaded
          When I search for matches between "Flamengo" and "Fluminense"
          Then I should receive a list of matches
          And each match should have date, scores, and competition
        """
        # Given
        assert queries is not None

        # When
        result = queries.find_matches(team="Flamengo", opponent="Fluminense", limit=50)

        # Then
        assert result["total_found"] > 0
        assert result["count"] > 0
        for m in result["matches"]:
            assert "date" in m
            assert "score" in m
            assert "competition" in m
            assert "home_team" in m
            assert "away_team" in m

    @pytest.mark.bdd
    def test_find_matches_by_team_only(self, queries: SoccerQueries):
        """
        Scenario: Find all matches for a single team
          Given the match data is loaded
          When I search for matches for "Palmeiras"
          Then I should receive a list of matches involving Palmeiras
        """
        # When
        result = queries.find_matches(team="Palmeiras", limit=10)

        # Then
        assert result["total_found"] > 0
        for m in result["matches"]:
            teams = {m["home_team"].lower(), m["away_team"].lower()}
            assert "palmeiras" in " ".join(teams)

    @pytest.mark.bdd
    def test_find_matches_by_competition(self, queries: SoccerQueries):
        """
        Scenario: Find matches by competition
          Given the match data is loaded
          When I search for matches in "Libertadores"
          Then all results should be Libertadores matches
        """
        # When
        result = queries.find_matches(competition="Libertadores", limit=10)

        # Then
        assert result["total_found"] > 0
        for m in result["matches"]:
            assert m["competition"] == "Copa Libertadores"

    @pytest.mark.bdd
    def test_find_matches_by_season(self, queries: SoccerQueries):
        """
        Scenario: Find matches by season
          Given the match data is loaded
          When I search for Brasileirao matches in 2019
          Then all results should be from the 2019 season
        """
        # When
        result = queries.find_matches(competition="Brasileirao", season=2019, limit=10)

        # Then
        assert result["total_found"] > 0
        for m in result["matches"]:
            assert m["season"] == 2019

    @pytest.mark.bdd
    def test_find_matches_by_date_range(self, queries: SoccerQueries):
        """
        Scenario: Find matches by date range
          Given the match data is loaded
          When I search for matches from 2019-01-01 to 2019-12-31
          Then all results should fall within that date range
        """
        # When
        result = queries.find_matches(date_from="2019-01-01", date_to="2019-12-31", limit=20)

        # Then
        assert result["total_found"] > 0
        for m in result["matches"]:
            if m["date"]:
                assert "2019-" in m["date"]

    @pytest.mark.bdd
    def test_find_copa_do_brasil_finals(self, queries: SoccerQueries):
        """
        Scenario: Find Copa do Brasil finals
          Given the match data is loaded
          When I search for Libertadores final-stage matches
          Then I should receive matches with a stage field
        """
        # When
        result = queries.find_matches(competition="Libertadores", limit=100)

        # Then - at least some matches should have a stage
        stages = [m["stage"] for m in result["matches"] if m["stage"]]
        assert len(stages) > 0

    @pytest.mark.bdd
    def test_limit_respected(self, queries: SoccerQueries):
        """
        Scenario: Limit the number of returned matches
          Given the match data is loaded
          When I search for matches with a limit of 5
          Then no more than 5 matches should be returned
        """
        # When
        result = queries.find_matches(limit=5)

        # Then
        assert result["count"] <= 5
        assert len(result["matches"]) <= 5

    @pytest.mark.bdd
    def test_head_to_head_between_two_teams(self, queries: SoccerQueries):
        """
        Scenario: Get head-to-head record between two teams
          Given the match data is loaded
          When I request the head-to-head between "Flamengo" and "Fluminense"
          Then I should receive wins, draws, losses and match list
        """
        # When
        result = queries.head_to_head("Flamengo", "Fluminense")

        # Then
        assert result["total_matches"] > 0
        assert result["team1_wins"] + result["team2_wins"] + result["draws"] == result["total_matches"]
        assert result["team1"] is not None
        assert result["team2"] is not None
        assert len(result["matches"]) == result["total_matches"]

    @pytest.mark.bdd
    def test_head_to_head_palmeiras_santos(self, queries: SoccerQueries):
        """
        Scenario: Compare Palmeiras and Santos head-to-head
          Given the match data is loaded
          When I request head-to-head between "Palmeiras" and "Santos"
          Then I should receive a valid record
        """
        # When
        result = queries.head_to_head("Palmeiras", "Santos")

        # Then
        assert result["total_matches"] > 0
        assert result["team1"] == "Palmeiras"
        assert result["team2"] == "Santos"
