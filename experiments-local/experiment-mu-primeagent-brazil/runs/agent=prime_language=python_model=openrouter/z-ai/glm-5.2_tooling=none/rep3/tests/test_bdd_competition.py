"""
Context Block
=============

Module: tests.test_bdd_competition
Purpose: BDD (Given-When-Then) scenarios for competition queries.
"""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp.queries import SoccerQueries


class TestCompetitionQueriesBDD:
    """BDD scenarios for the Competition Queries feature."""

    @pytest.mark.bdd
    def test_brasileirao_2019_champion(self, queries: SoccerQueries):
        """
        Scenario: Who won the 2019 Brasileirao?
          Given the match data is loaded
          When I request the 2019 Brasileirao standings
          Then Flamengo should be the champion
          And the standings should be sorted by points
        """
        # When
        result = queries.competition_standings("Brasileirao", season=2019)

        # Then
        assert result["champion"] is not None
        assert "Flamengo" in result["champion"]
        # Standings sorted by points
        points = [s["points"] for s in result["standings"]]
        assert points == sorted(points, reverse=True)

    @pytest.mark.bdd
    def test_brasileirao_2018_champion(self, queries: SoccerQueries):
        """
        Scenario: Who won the 2018 Brasileirao?
          Given the match data is loaded
          When I request the 2018 Brasileirao standings
          Then Palmeiras should be the champion
        """
        # When
        result = queries.competition_standings("Brasileirao", season=2018)

        # Then
        assert result["champion"] is not None
        assert "Palmeiras" in result["champion"]

    @pytest.mark.bdd
    def test_standings_have_required_fields(self, queries: SoccerQueries):
        """
        Scenario: Standings include all required fields
          Given the match data is loaded
          When I request Brasileirao 2019 standings
          Then each entry should have position, team, points, W/D/L
        """
        # When
        result = queries.competition_standings("Brasileirao", season=2019)

        # Then
        assert len(result["standings"]) > 0
        for s in result["standings"]:
            assert "position" in s
            assert "team" in s
            assert "points" in s
            assert "wins" in s
            assert "draws" in s
            assert "losses" in s
            assert "played" in s
            assert s["wins"] + s["draws"] + s["losses"] == s["played"]

    @pytest.mark.bdd
    def test_competition_seasons(self, queries: SoccerQueries):
        """
        Scenario: List seasons for a competition
          Given the match data is loaded
          When I request seasons for Brasileirao
          Then I should receive a list of years
        """
        # When
        result = queries.competition_seasons("Brasileirao")

        # Then
        assert len(result["seasons"]) > 0
        # Should include 2019
        assert 2019 in result["seasons"]

    @pytest.mark.bdd
    def test_competition_info(self, queries: SoccerQueries):
        """
        Scenario: Get competition summary
          Given the match data is loaded
          When I request info for Libertadores
          Then I should receive match count and seasons
        """
        # When
        result = queries.competition_info("Libertadores")

        # Then
        assert result["total_matches"] > 0
        assert len(result["seasons"]) > 0

    @pytest.mark.bdd
    def test_all_competitions(self, queries: SoccerQueries):
        """
        Scenario: List all competitions
          Given the match data is loaded
          When I request all competitions
          Then I should receive all competition types
        """
        # When
        result = queries.all_competitions()

        # Then
        names = [c["name"] for c in result["competitions"]]
        assert "Brasileirao" in names
        assert "Copa do Brasil" in names
        assert "Copa Libertadores" in names

    @pytest.mark.bdd
    def test_standings_points_calculation(self, queries: SoccerQueries):
        """
        Scenario: Points are calculated correctly (3 for win, 1 for draw)
          Given the match data is loaded
          When I request Brasileirao 2019 standings
          Then points should equal 3*wins + 1*draws
        """
        # When
        result = queries.competition_standings("Brasileirao", season=2019)

        # Then
        for s in result["standings"]:
            expected_points = 3 * s["wins"] + 1 * s["draws"]
            assert s["points"] == expected_points, f"{s['team']}: {s['points']} != {expected_points}"

    @pytest.mark.bdd
    def test_invalid_competition(self, queries: SoccerQueries):
        """
        Scenario: Querying a non-existent competition returns an error
          Given the match data is loaded
          When I request standings for a non-existent competition
          Then I should receive an error message
        """
        # When
        result = queries.competition_standings("NonExistent Competition")

        # Then
        assert "error" in result
