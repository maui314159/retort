"""BDD scenarios for player queries (TASK.md "Player Queries").

Feature: Player Queries
  Scenario: Search players
    Given the FIFA player database is loaded
    When I search for Brazilian players with a high rating
    Then I should receive players with name, overall, position and club

Note: the FIFA snapshot does not include Flamengo, Palmeiras,
Corinthians, São Paulo or Vasco (licensing), so scenarios also assert
graceful empty results for those clubs.
"""

from __future__ import annotations

from server import get_club_players, get_player_details, search_players


class TestSearchPlayers:
    """Gherkin: 'Find all Brazilian players in the dataset'."""

    def test_top_rated_brazilian_players(self, data):
        """
        Scenario: top-rated Brazilians
          Given the FIFA database
          When I search Brazilian players with overall >= 88
          Then Neymar Jr appears first and every result is Brazilian
        """
        result = search_players(nationality="Brazil", min_overall=88)
        players = result["data"]["players"]
        assert players[0]["name"] == "Neymar Jr"
        assert players[0]["overall"] == 92
        assert all(p["nationality"] == "Brazil" for p in players)

    def test_search_by_name(self, data):
        """
        Scenario: search by name
          Given the FIFA database
          When I search for "Casemiro"
          Then the Real Madrid midfielder is returned
        """
        result = search_players(name="Casemiro")
        names = [p["name"] for p in result["data"]["players"]]
        assert "Casemiro" in names
        casemiro = next(p for p in result["data"]["players"] if p["name"] == "Casemiro")
        assert casemiro["position"] == "CDM"
        assert casemiro["nationality"] == "Brazil"

    def test_filter_by_club_and_nationality(self, data):
        """
        Scenario: Brazilians at a foreign club
          Given the FIFA database
          When I search Brazilian players at Paris Saint-Germain
          Then only PSG players with Brazilian nationality are returned
        """
        result = search_players(club="Paris Saint-Germain", nationality="Brazil")
        assert 0 < result["data"]["count"] <= 10
        for player in result["data"]["players"]:
            assert player["nationality"] == "Brazil"
            assert "Paris Saint-Germain" in player["club"]

    def test_filter_by_position_group(self, data):
        """
        Scenario: position groups
          Given the FIFA database
          When I search Brazilian goalkeepers
          Then every result plays in goal
        """
        result = search_players(nationality="Brazil", position="goalkeeper", limit=10)
        assert result["data"]["count"] > 0
        for player in result["data"]["players"]:
            assert player["position"] == "GK"

    def test_sort_by_potential(self, data):
        """
        Scenario: young talents
          Given the FIFA database
          When I search Brazilian players under 21 sorted by potential
          Then results are ordered by descending potential
        """
        result = search_players(
            nationality="Brazil", max_age=20, sort="potential", limit=10
        )
        players = result["data"]["players"]
        potentials = [p["potential"] for p in players]
        assert potentials == sorted(potentials, reverse=True)
        assert all(p["age"] <= 20 for p in players)


class TestPlayerDetails:
    """Gherkin: 'Who is Gabriel Barbosa?' (FIFA-era equivalent)."""

    def test_player_profile_includes_attributes(self, data):
        """
        Scenario: player details
          Given the FIFA database
          When I look up "Gabriel Jesus"
          Then a full profile with ratings and skills is returned
        """
        result = get_player_details("Gabriel Jesus")
        player = result["data"]["players"][0]
        assert player["name"] == "Gabriel Jesus"
        assert player["nationality"] == "Brazil"
        assert player["position"] == "ST"
        assert player["overall"] == 83
        assert "Finishing" in player["skills"]
        assert result["data"]["matches_found"] >= 1

    def test_player_not_in_dataset(self, data):
        """
        Scenario: player absent from the FIFA snapshot
          Given "Gabriel Barbosa" (who is not in this FIFA edition)
          When I look him up
          Then a clear error is returned
        """
        result = get_player_details("Gabriel Barbosa")
        assert "error" in result


class TestClubSquads:
    """Gherkin: 'Which players play for Flamengo?' and cross-file queries."""

    def test_gremio_squad_with_average_rating(self, data):
        """
        Scenario: squad listing
          Given Grêmio exists in the FIFA database
          When I request the Grêmio squad
          Then players, average rating and match data are returned
        """
        result = get_club_players("Grêmio")
        payload = result["data"]
        assert payload["squad_size"] >= 20
        assert payload["club"] == "Grêmio"
        assert payload["match_record"]["matches"] > 500
        assert result["summary"].startswith("Grêmio squad")

    def test_flamengo_players_absent_but_matches_present(self, data):
        """
        Scenario: club missing from FIFA data (cross-file boundary)
          Given Flamengo has 1000+ matches but no FIFA players
          When I request the Flamengo squad
          Then the answer notes the licensing gap and still returns
            the club's match record
        """
        result = get_club_players("Flamengo")
        payload = result["data"]
        assert payload["squad_size"] == 0
        assert payload["match_record"]["matches"] > 500
        assert "no Flamengo players" in result["summary"].lower() or \
            "not" in result["summary"].lower()

    def test_brazilian_players_at_brazilian_clubs(self, data):
        """
        Scenario: Brazilians at Brazilian clubs
          Given the FIFA database
          When I request the Santos squad filtered to Brazilians
          Then every listed player is Brazilian
        """
        result = get_club_players("Santos", nationality="Brazil")
        assert result["data"]["squad_size"] > 0
        for player in result["data"]["squad"]:
            assert player["nationality"] == "Brazil"

    def test_club_cross_file_query_binds_player_and_match_data(self, data):
        """
        Scenario: cross-file query
          Given the FIFA database and the match datasets
          When I request a club profile
          Then both squad information and the match record appear in one
            response
        """
        result = get_club_players("Cruzeiro")
        payload = result["data"]
        assert payload["squad_size"] > 0
        assert payload["recent_matches"]
        assert payload["match_record"]["matches"] > 400
