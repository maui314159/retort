"""Feature: Player Queries

Background:
    Given the FIFA player database is loaded (18,207 players)
"""

from __future__ import annotations

import pytest

from brazilian_soccer import query
from brazilian_soccer.query import QueryError


class TestSearchPlayerByName:
    """Scenario: Who is a given player?
        Given the FIFA player data
        When I search for a player by name
        Then I should receive their ratings, club and position
    """

    def test_given_neymar_when_searching_by_name_then_rating_and_club_returned(self, dataset):
        result = query.search_players(dataset, name="Neymar")
        assert result["total"] >= 1
        neymar = result["players"][0]
        assert neymar["name"] == "Neymar Jr"
        assert neymar["overall"] == 92
        assert neymar["position"] == "LW"
        assert "Paris Saint-Germain" in neymar["club"]

    def test_given_partial_name_when_searching_then_substring_match(self, dataset):
        result = query.search_players(dataset, name="Casemiro")
        assert any(p["name"] == "Casemiro" for p in result["players"])

    def test_given_unknown_player_when_searching_then_empty_result(self, dataset):
        result = query.search_players(dataset, name="Gabriel Barbosa")
        assert result["total"] == 0
        assert result["players"] == []


class TestFindBrazilianPlayers:
    """Scenario: Find all Brazilian players in the dataset
        Given the FIFA player data
        When I filter by nationality Brazil
        Then hundreds of players should be returned
    """

    def test_given_brazil_nationality_when_filtering_then_many_players(self, dataset):
        result = query.search_players(dataset, nationality="Brazil", limit=5)
        assert result["total"] > 700
        assert len(result["players"]) == 5

    def test_given_brazil_nationality_when_filtering_then_all_results_brazilian(self, dataset):
        result = query.search_players(dataset, nationality="Brazil", limit=50)
        assert all(p["nationality"] == "Brazil" for p in result["players"])

    def test_given_top_brazilian_players_when_ranking_then_headlined_by_neymar(self, dataset):
        result = query.top_players(dataset, nationality="Brazil", limit=5)
        assert result["players"][0]["name"] == "Neymar Jr"
        ratings = [p["overall"] for p in result["players"]]
        assert ratings == sorted(ratings, reverse=True)


class TestPlayersAtClub:
    """Scenario: Which players play for a club?
        Given the FIFA data covers selected Brazilian clubs
        When I filter by club
        Then the squad should be returned sorted by rating
    """

    def test_given_gremio_when_filtering_by_club_then_full_squad_returned(self, dataset):
        result = query.search_players(dataset, club="Grêmio", limit=30)
        assert result["total"] == 20
        ratings = [p["overall"] for p in result["players"]]
        assert ratings == sorted(ratings, reverse=True)
        assert all(p["club"] == "Grêmio" for p in result["players"])

    def test_given_club_name_variants_when_filtering_then_same_squad(self, dataset):
        exact = query.search_players(dataset, club="Grêmio", limit=30)
        variant = query.search_players(dataset, club="Gremio", limit=30)
        assert exact["total"] == variant["total"] == 20

    def test_given_club_absent_from_fifa_data_when_filtering_then_empty(self, dataset):
        result = query.search_players(dataset, club="Flamengo")
        assert result["total"] == 0


class TestPlayersByPosition:
    """Scenario: Show me all forwards from a club
        Given the FIFA data
        When I filter by position group
        Then only players in that group should be returned
    """

    def test_given_forwards_at_santos_when_filtering_then_forwards_returned(self, dataset):
        result = query.search_players(dataset, club="Santos", position="forward", limit=30)
        forward_codes = {"ST", "LS", "RS", "CF", "LF", "RF", "LW", "RW"}
        assert result["total"] > 0
        assert all(p["position"] in forward_codes for p in result["players"])

    def test_given_goalkeeper_group_when_filtering_then_only_gk(self, dataset):
        result = query.search_players(dataset, club="Santos", position="goalkeeper", limit=30)
        assert result["total"] > 0
        assert all(p["position"] == "GK" for p in result["players"])

    def test_given_invalid_position_when_filtering_then_error(self, dataset):
        with pytest.raises(QueryError):
            query.search_players(dataset, position="winger-osopher")


class TestPlayersByClubAggregation:
    """Scenario: Brazilian players at Brazilian clubs
        Given the FIFA data and the list of Brazilian clubs from match data
        When I aggregate players per club
        Then each Brazilian club with Brazilians should be listed with counts and ratings
    """

    def test_given_brazilians_at_brazilian_clubs_when_aggregating_then_clubs_listed(self, dataset):
        result = query.players_by_club(dataset)
        assert result["total_clubs"] >= 10
        for club in result["clubs"]:
            assert club["players"] > 0
            assert club["avg_overall"] > 60
        names = {c["club"] for c in result["clubs"]}
        assert "Grêmio" in names
        assert "Santos" in names

    def test_given_foreign_clubs_when_aggregating_brazilians_then_excluded_by_default(self, dataset):
        result = query.players_by_club(dataset)
        names = {c["club"] for c in result["clubs"]}
        assert "Paris Saint-Germain" not in names


class TestOverallRatingFilters:
    """Scenario: Filter players by rating
        Given the FIFA data
        When I bound the overall rating
        Then only players within bounds should be returned
    """

    def test_given_min_overall_90_when_filtering_then_elite_players_only(self, dataset):
        result = query.search_players(dataset, min_overall=90, limit=30)
        assert result["total"] > 0
        assert all(p["overall"] >= 90 for p in result["players"])
