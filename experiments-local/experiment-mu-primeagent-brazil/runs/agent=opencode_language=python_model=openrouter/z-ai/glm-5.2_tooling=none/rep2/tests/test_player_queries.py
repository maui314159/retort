"""BDD tests: player queries against the FIFA database.

Feature: Player Queries
  Scenario: Find Brazilian players
    Given the FIFA player data is loaded
    When I search for players of nationality "Brazil" ordered by Overall
    Then the first result should be Neymar Jr with overall 92

  Scenario: Find players by club
    Given the FIFA player data is loaded
    When I search for players whose club contains "Flamengo"
    Then every returned player's club contains "Flamengo"
"""
from __future__ import annotations

from brsl.query_engine import QueryEngine


class TestPlayerQueries:
    # Scenario: top Brazilian players
    def test_top_brazilian_players(self, engine: QueryEngine):
        result = engine.top_brazilian_players(limit=10)
        assert result["count"] > 500
        players = result["players"]
        assert players, "expected at least one player"
        # The highest-rated Brazilian in this FIFA snapshot is Neymar Jr (92).
        assert players[0]["name"] == "Neymar Jr"
        assert players[0]["overall"] == 92
        # ordering is by Overall descending
        overalls = [p["overall"] for p in players if p["overall"]]
        assert overalls == sorted(overalls, reverse=True)

    # Scenario: search by name
    def test_search_player_by_name(self, engine: QueryEngine):
        result = engine.search_players(name="Neymar")
        assert result["count"] >= 1
        assert any("Neymar" in p["name"] for p in result["players"])

    # Scenario: search by club (Botafogo is present in the FIFA snapshot;
    # Flamengo is not, so we query a club that exists in both datasets).
    def test_search_players_by_club(self, engine: QueryEngine):
        result = engine.search_players(club="Botafogo", limit=50)
        assert result["count"] > 0
        for p in result["players"]:
            assert "Botafogo" in p["club"]

    # Scenario: Brazilian players grouped by Brazilian club
    def test_players_at_brazilian_clubs(self, engine: QueryEngine):
        result = engine.players_at_brazilian_clubs(limit=10)
        assert len(result["clubs"]) > 0
        for c in result["clubs"]:
            assert c["players"] > 0
            assert c["avg_overall"] is not None

    # Scenario: filter by position
    def test_search_by_position(self, engine: QueryEngine):
        result = engine.search_players(position="GK", nationality="Brazil",
                                       limit=10)
        for p in result["players"]:
            assert p["position"] == "GK"

    # Scenario: minimum overall filter
    def test_min_overall_filter(self, engine: QueryEngine):
        result = engine.search_players(min_overall=90, limit=10)
        for p in result["players"]:
            assert p["overall"] >= 90

    # Scenario: cross-file - team players (club in FIFA) from a match team name
    def test_team_players_cross_file(self, engine: QueryEngine):
        # Botafogo appears in both the match datasets and the FIFA database,
        # so the cross-file player lookup returns a non-empty roster.
        result = engine.team_players("Botafogo", limit=10)
        assert result["count"] > 0
