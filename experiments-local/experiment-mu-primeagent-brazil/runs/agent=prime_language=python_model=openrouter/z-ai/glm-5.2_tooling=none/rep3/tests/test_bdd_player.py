"""
Context Block
=============

Module: tests.test_bdd_player
Purpose: BDD (Given-When-Then) scenarios for player queries.
"""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp.queries import SoccerQueries


class TestPlayerQueriesBDD:
    """BDD scenarios for the Player Queries feature."""

    @pytest.mark.bdd
    def test_find_brazilian_players(self, queries: SoccerQueries):
        """
        Scenario: Find all Brazilian players
          Given the FIFA player data is loaded
          When I search for players with nationality "Brazil"
          Then I should receive a list of Brazilian players
        """
        # When
        result = queries.find_players(nationality="Brazil", limit=50)

        # Then
        assert result["total_found"] > 100
        for p in result["players"]:
            assert p["nationality"] == "Brazil"

    @pytest.mark.bdd
    def test_find_players_by_name(self, queries: SoccerQueries):
        """
        Scenario: Find a player by name
          Given the FIFA player data is loaded
          When I search for "Neymar"
          Then I should receive players whose name contains Neymar
        """
        # When
        result = queries.find_players(name="Neymar")

        # Then
        assert result["total_found"] > 0
        for p in result["players"]:
            assert "neymar" in p["name"].lower()

    @pytest.mark.bdd
    def test_top_brazilian_players(self, queries: SoccerQueries):
        """
        Scenario: Top Brazilian players by rating
          Given the FIFA player data is loaded
          When I request the top 5 Brazilian players
          Then I should receive players sorted by overall rating
        """
        # When
        result = queries.top_players(nationality="Brazil", limit=5)

        # Then
        assert result["count"] == 5
        ratings = [p["overall"] for p in result["players"]]
        assert ratings == sorted(ratings, reverse=True)
        # Neymar should be among the top Brazilian players
        assert any("neymar" in p["name"].lower() for p in result["players"])

    @pytest.mark.bdd
    def test_find_players_by_club(self, queries: SoccerQueries):
        """
        Scenario: Find players by club
          Given the FIFA player data is loaded
          When I search for players at "Santos"
          Then I should receive players whose club is Santos
        """
        # When
        result = queries.find_players(club="Santos", limit=50)

        # Then
        assert result["total_found"] > 0
        for p in result["players"]:
            assert p["club"] is not None

    @pytest.mark.bdd
    def test_find_players_by_position(self, queries: SoccerQueries):
        """
        Scenario: Find all forwards from a position
          Given the FIFA player data is loaded
          When I search for players in position "ST"
          Then I should receive players whose position is ST
        """
        # When
        result = queries.find_players(position="ST", limit=20)

        # Then
        assert result["total_found"] > 0
        for p in result["players"]:
            assert p["position"] == "ST"

    @pytest.mark.bdd
    def test_filter_by_min_rating(self, queries: SoccerQueries):
        """
        Scenario: Filter players by minimum rating
          Given the FIFA player data is loaded
          When I search for players with overall >= 90
          Then all returned players should have rating >= 90
        """
        # When
        result = queries.find_players(min_rating=90, limit=50)

        # Then
        for p in result["players"]:
            assert p["overall"] >= 90

    @pytest.mark.bdd
    def test_players_at_brazilian_clubs(self, queries: SoccerQueries):
        """
        Scenario: Players at Brazilian clubs
          Given the FIFA data and match data are loaded
          When I request players at Brazilian clubs
          Then I should receive players whose club is a Brazilian team
        """
        # When
        result = queries.players_at_brazilian_clubs(min_rating=70, limit=20)

        # Then
        assert result["total_found"] > 0
        for p in result["players"]:
            assert p["club"] is not None
