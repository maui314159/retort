"""BDD scenarios for player queries against the FIFA dataset.

Feature: Player queries
  Scenario: Find players by nationality and rating
    Given the FIFA player database is loaded
    When I search for Brazilian players sorted by overall rating
    Then the highest-rated Brazilians are returned first
"""

from __future__ import annotations

import re


class TestSearchPlayers:
    def test_search_by_name_finds_neymar(self, svc):
        # Given the FIFA database is loaded
        # When I search for "Neymar"
        result = svc.search_players(name="Neymar")
        # Then Neymar Jr's profile comes back with rating and club
        assert "Neymar Jr" in result
        assert "Overall: 92" in result
        assert "Paris Saint-Germain" in result
        assert "Nationality: Brazil" in result

    def test_top_brazilian_players_are_ranked_by_rating(self, svc):
        # Given 827 Brazilian players
        # When I list them by overall rating
        result = svc.search_players(nationality="Brazil", limit=5)
        # Then Neymar Jr is first and ratings descend
        assert "1. Neymar Jr - Overall: 92" in result
        overalls = [int(m) for m in re.findall(r"Overall: (\d+)", result)]
        assert overalls == sorted(overalls, reverse=True)

    def test_filter_by_minimum_rating(self, svc):
        # Given players of many ratings
        # When I filter to overall >= 90
        result = svc.search_players(min_overall=90, limit=30)
        # Then only 90+ players are returned
        overalls = [int(m) for m in re.findall(r"Overall: (\d+)", result)]
        assert overalls and all(o >= 90 for o in overalls)

    def test_unlicensed_club_returns_helpful_note(self, svc):
        # Given Flamengo is not in the FIFA dataset (licensing)
        # When I search for its players
        result = svc.search_players(club="Flamengo")
        # Then the licensing note explains the empty result
        assert "No players found" in result
        assert "licensing" in result

    def test_forwards_at_santos(self, svc):
        # Given position codes and role groups
        # When I ask for forwards from Santos
        result = svc.search_players(club="Santos", position="Forward", limit=30)
        # Then every returned player is a forward at a Santos club
        assert "found" in result
        for line in result.splitlines():
            if not line[0].isdigit():
                continue
            assert "(Forward)" in line, line
            assert "Club: Santos" in line, line

    def test_position_code_filter_works(self, svc):
        # Given the FIFA position code "GK"
        # When I filter Brazilian goalkeepers
        result = svc.search_players(nationality="Brazil", position="GK", limit=5)
        # Then only goalkeepers are returned
        assert result.count("GK (Goalkeeper)") >= 1
        assert "(Forward)" not in result

    def test_free_agents_never_match_a_club_filter(self, svc):
        # Given 241 players have no club
        # When I filter by any club
        result = svc.search_players(club="Grêmio", limit=30)
        # Then no "No club" player leaks into the results
        assert "Club: No club" not in result


class TestPlayersByClub:
    def test_brazilian_players_at_brazilian_clubs(self, svc):
        # Given Brazilian players at Brazilian league clubs
        # When I aggregate by club
        result = svc.players_by_club(nationality="Brazil", limit=20)
        # Then known licensed clubs appear with counts and average ratings
        for club in ("Grêmio", "Atlético-MG", "Cruzeiro", "Fluminense"):
            assert re.search(rf"- {club}: \d+ players \(avg rating: \d+\)", result), club

    def test_aggregation_can_include_foreign_clubs(self, svc):
        # Given Brazilians also play abroad
        # When I include all clubs
        result = svc.players_by_club(
            nationality="Brazil", brazilian_clubs_only=False, limit=25
        )
        # Then major foreign clubs appear
        assert "Portimonense" in result or "Paris Saint-Germain" in result
