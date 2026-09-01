"""Feature: Player Queries

BDD scenarios for the TASK.md examples:
- "Who is Gabriel Barbosa?" (name search with graceful miss)
- "Who are the highest-rated players at a club?"
- "Find all Brazilian players in the dataset"
- "Show me all forwards from a club"
"""

from __future__ import annotations

import pytest

from brazilian_soccer import queries as q


class TestSearchPlayersByName:
    """Feature: Player Queries - Scenario: search by name."""

    def test_exact_name_lookup(self, soccer):
        """Scenario: 'Who is Neymar Jr?'"""
        # Given the FIFA player data is loaded
        # When I search for the name "Neymar Jr"
        result = q.search_players(soccer, name="Neymar Jr")
        # Then I receive the player with his ratings
        assert result["total_matches"] == 1
        player = result["players"][0]
        assert player["name"] == "Neymar Jr"
        assert player["nationality"] == "Brazil"
        assert player["overall"] == 92
        assert player["club"] == "Paris Saint-Germain"
        assert player["position"] == "LW"

    def test_name_substring_matches(self, soccer):
        # Given the FIFA data is loaded
        # When I search for the substring "Gabriel Jesus"
        result = q.search_players(soccer, name="Gabriel Jesus")
        # Then the Manchester City forward is found
        assert result["total_matches"] == 1
        player = result["players"][0]
        assert player["overall"] == 83
        assert player["potential"] == 92
        assert player["club"] == "Manchester City"

    def test_unknown_name_suggests_similar_players(self, soccer):
        """Scenario: 'Who is Gabriel Barbosa?' (not in this FIFA dataset)."""
        # Given the FIFA dataset does not contain Gabriel Barbosa
        # When I search for his name
        result = q.search_players(soccer, name="Gabriel Barbosa")
        # Then no match is returned but similar players are suggested
        assert result["total_matches"] == 0
        assert "No player named" in result["note"]
        suggested = [p["name"] for p in result["similar_players"]]
        assert "Gabriel Jesus" in suggested
        assert "Gabriel Paulista" in suggested


class TestFilterPlayers:
    """Feature: Player Queries - Scenario: filter by nationality, club, position."""

    def test_all_brazilian_players_in_the_dataset(self, soccer):
        # Given the FIFA data is loaded
        # When I filter by nationality "Brazil"
        result = q.search_players(soccer, nationality="Brazil", limit=1)
        # Then the full contingent is counted
        assert result["total_matches"] == 827
        assert result["truncated"] is True

    def test_top_rated_brazilian_players(self, soccer):
        """Scenario: 'Who are the top Brazilian players?'"""
        # Given the FIFA data is loaded
        # When I filter Brazilians with overall >= 88 sorted by rating
        result = q.search_players(soccer, nationality="Brazil", min_overall=88)
        # Then Neymar Jr leads the list
        players = result["players"]
        assert players[0]["name"] == "Neymar Jr"
        assert players[0]["overall"] == 92
        names = [p["name"] for p in players]
        assert "Casemiro" in names
        assert all(p["nationality"] == "Brazil" for p in players)
        assert all(p["overall"] >= 88 for p in players)

    def test_players_at_a_club(self, soccer):
        """Scenario: 'Which players play for Grêmio?'"""
        # Given the FIFA data is loaded
        # When I filter by club "Grêmio"
        result = q.search_players(soccer, club="Grêmio", limit=50)
        # Then the squad is returned sorted by rating
        assert result["total_matches"] == 20
        assert all(p["club"] == "Grêmio" for p in result["players"])
        overalls = [p["overall"] for p in result["players"]]
        assert overalls == sorted(overalls, reverse=True)

    def test_forwards_from_a_club(self, soccer):
        """Scenario: 'Show me all forwards from Santos'."""
        # Given the FIFA data is loaded
        # When I filter club "Santos" to the forwards group
        result = q.search_players(soccer, club="Santos", position_group="forwards", limit=50)
        # Then every returned player is a forward at a matching club
        assert result["total_matches"] == 9
        forward_positions = {"ST", "LS", "RS", "LW", "RW", "LF", "RF", "CF"}
        assert all(p["position"] in forward_positions for p in result["players"])
        # And per the spec the club filter is a containment match,
        # which also picks up e.g. Santos Laguna
        assert all("santos" in p["club"].lower() for p in result["players"])
        assert set(result["matched_clubs"]) == {"Santos", "Santos Laguna"}

    def test_brazilian_goalkeepers_by_rating(self, soccer):
        # Given the FIFA data is loaded
        # When I ask for Brazilian goalkeepers rated 85+
        result = q.search_players(
            soccer, nationality="Brazil", position="GK", min_overall=85, limit=10
        )
        # Then Ederson and Alisson are found
        names = {p["name"] for p in result["players"]}
        assert names == {"Ederson", "Alisson"}
        assert all(p["position"] == "GK" for p in result["players"])

    def test_sort_by_potential(self, soccer):
        # Given the FIFA data is loaded
        # When I sort Brazilians by potential
        result = q.search_players(soccer, nationality="Brazil", sort="potential", limit=3)
        # Then the highest-potential youngsters lead
        top = result["players"][0]
        assert top["name"] == "Neymar Jr"
        assert top["potential"] == 93
        potentials = [p["potential"] for p in result["players"]]
        assert potentials == sorted(potentials, reverse=True)

    def test_invalid_position_group_is_rejected(self, soccer):
        # Given an unknown position group
        # When I search
        # Then a helpful error is raised
        with pytest.raises(ValueError, match="position_group"):
            q.search_players(soccer, position_group="wingers")

    def test_player_payload_fields(self, soccer):
        # Given any player search
        # When results are returned
        result = q.search_players(soccer, name="Casemiro")
        # Then the payload carries the documented fields
        player = result["players"][0]
        for field in ("id", "name", "age", "nationality", "overall", "potential",
                      "club", "position", "jersey_number", "value_eur"):
            assert field in player
        assert player["value_eur"] == 59_500_000
