"""BDD scenarios for player queries.

Feature: Player Queries
  Users ask about players by name, nationality, club, position and
  rating, using the FIFA player database.
"""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp.models import Player
from brazilian_soccer_mcp.normalize import TeamNotFoundError
from brazilian_soccer_mcp.queries import QueryError


class TestTopBrazilianPlayers:
    """
    Scenario: Who are the top Brazilian players?
      Given the FIFA player database is loaded
      When I search for Brazilian players ordered by rating
      Then Neymar Jr (92) is first
    """

    def test_when_searching_brazilian_players_then_827_are_found(self, engine):
        players = engine.search_players(nationality="Brazil", limit=2000)
        assert len(players) == 827
        assert all(p.nationality == "Brazil" for p in players)

    def test_when_searching_top_brazilians_then_neymar_is_first(self, engine):
        players = engine.search_players(nationality="Brazil", limit=5)
        assert players[0].name == "Neymar Jr"
        assert players[0].overall == 92
        assert players[0].position == "LW"
        ratings = [p.overall for p in players]
        assert ratings == sorted(ratings, reverse=True)

    def test_when_searching_with_an_adjectival_nationality_then_it_matches(self, engine):
        players = engine.search_players(nationality="Brazilian", limit=10)
        assert len(players) == 10
        assert all(p.nationality == "Brazil" for p in players)


class TestPlayerSearchByName:
    """
    Scenario: Who is Gabriel Barbosa?
      Given the FIFA player database is loaded
      When I search for the name "Gabriel Barbosa"
      Then no player matches and similar names are suggested
    """

    def test_when_searching_gabriel_barbosa_then_suggestions_are_offered(self, engine):
        with pytest.raises(TeamNotFoundError) as excinfo:
            engine.search_players(name="Gabriel Barbosa")
        suggestions = " ".join(excinfo.value.suggestions)
        assert "Gabriel" in suggestions

    def test_when_searching_a_real_name_then_the_player_is_found(self, engine):
        players = engine.search_players(name="Neymar")
        assert players
        assert players[0].name == "Neymar Jr"

    def test_when_searching_by_partial_name_then_all_matches_share_the_substring(self, engine):
        players = engine.search_players(name="Casemiro")
        assert len(players) == 1
        assert players[0].position == "CDM"


class TestPlayersAtClubs:
    """
    Scenario: Which players play for Fluminense?
      Given the FIFA player database is loaded
      When I request the Fluminense roster
      Then twenty players are returned with ratings
    """

    def test_when_requesting_the_fluminense_roster_then_twenty_players_appear(self, engine):
        roster = engine.club_players("Fluminense")
        assert len(roster) == 20
        assert all(p.club_key == "fluminense-rj" for p in roster)
        ratings = [p.overall for p in roster]
        assert ratings == sorted(ratings, reverse=True)

    def test_when_requesting_a_roster_for_a_club_not_in_the_fifa_data_then_it_is_reported(self, engine):
        players = engine.club_players("Palmeiras")
        assert players == []

    def test_when_players_are_found_by_club_then_the_club_key_matches_the_match_data(self, engine):
        roster = engine.club_players("Ceará")
        assert roster
        assert roster[0].club_key == "ceara"
        matches = engine.search_matches(team="Ceará", season=2019, limit=1)
        assert matches.total > 0


class TestPlayersByPosition:
    """
    Scenario: Show me all forwards from Santos
      Given the FIFA player database is loaded
      When I search forwards at Santos
      Then every player has a forward position
    """

    def test_when_searching_santos_forwards_then_only_attacking_positions_returned(self, engine):
        forwards = engine.search_players(club="Santos", position="forward", limit=50)
        attacking = {"ST", "LS", "RS", "CF", "LF", "RF", "LW", "RW"}
        assert forwards
        assert all(p.position in attacking for p in forwards)

    def test_when_searching_by_fifa_position_code_then_exact_positions_returned(self, engine):
        keepers = engine.search_players(club="Fluminense", position="GK", limit=10)
        assert keepers
        assert all(p.position == "GK" for p in keepers)

    def test_when_searching_an_unknown_position_then_an_error_is_raised(self, engine):
        with pytest.raises(QueryError):
            engine.search_players(position="winger-keeper")


class TestPlayerAttributes:
    """
    Scenario: Player ratings and attributes are available
      Given the FIFA player database is loaded
      When I request a player
      Then overall, potential and skill attributes are present
    """

    def test_when_reading_a_player_then_core_attributes_are_populated(self, engine):
        neymar = engine.search_players(name="Neymar")[0]
        assert isinstance(neymar, Player)
        assert neymar.potential >= neymar.overall
        assert neymar.nationality == "Brazil"
        assert neymar.skills.get("Dribbling", 0) > 90

    def test_when_ordering_by_potential_then_the_order_changes_from_overall(self, engine):
        by_overall = engine.search_players(nationality="Brazil", order_by="overall", limit=5)
        by_potential = engine.search_players(nationality="Brazil", order_by="potential", limit=5)
        names_overall = [p.name for p in by_overall]
        names_potential = [p.name for p in by_potential]
        assert names_overall[0] == "Neymar Jr"
        assert names_potential != names_overall

    def test_when_filtering_by_minimum_rating_then_all_results_meet_it(self, engine):
        stars = engine.search_players(nationality="Brazil", min_overall=85, limit=50)
        assert stars
        assert all(p.overall >= 85 for p in stars)
