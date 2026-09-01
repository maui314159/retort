"""BDD scenarios for player queries against the FIFA dataset.

Feature: Player queries
  Users search players by name, nationality, club and position, and ask
  for the highest-rated players at a club or from Brazil.
"""

from __future__ import annotations


def test_search_player_by_name(service):
    """Scenario: Who is Neymar Jr?
    Given the FIFA dataset contains Neymar Jr
    When I search for players named "Neymar"
    Then his profile with rating, position and club is returned
    """
    # Given
    name = "Neymar"

    # When
    result = service.search_players(name=name)

    # Then
    assert result["total"] == 1
    player = result["players"][0]
    assert player["name"] == "Neymar Jr"
    assert player["overall"] == 92
    assert player["position"] == "LW"
    assert player["club"] == "Paris Saint-Germain"
    assert player["nationality"] == "Brazil"
    assert player["jersey_number"] == 10


def test_search_missing_player_returns_empty(service):
    """Scenario: Who is Gabriel Barbosa?
    Given a player is not in the FIFA dataset
    When I search for him by name
    Then an empty result is returned without errors
    """
    # Given / When
    result = service.search_players(name="Gabriel Barbosa")

    # Then
    assert result["total"] == 0
    assert result["players"] == []


def test_find_all_brazilian_players(service):
    """Scenario: Find all Brazilian players in the dataset
    Given the FIFA dataset contains 827 Brazilians
    When I filter by nationality "Brazil"
    Then every result is Brazilian and sorted by rating
    """
    # Given / When
    result = service.search_players(nationality="Brazil", limit=200)

    # Then
    assert result["total"] == 827
    overalls = [p["overall"] for p in result["players"]]
    assert overalls == sorted(overalls, reverse=True)
    assert all(p["nationality"] == "Brazil" for p in result["players"])


def test_top_brazilian_players(service):
    """Scenario: Who are the top Brazilian players?
    Given Brazilians are ranked by FIFA overall rating
    When I ask for the top five
    Then Neymar Jr leads the list
    """
    # Given / When
    result = service.top_players(nationality="Brazil", limit=5)

    # Then
    assert result["players"][0]["name"] == "Neymar Jr"
    assert result["players"][0]["overall"] == 92
    names = [p["name"] for p in result["players"]]
    assert "Casemiro" in names
    assert all(p["nationality"] == "Brazil" for p in result["players"])


def test_players_at_a_club(service):
    """Scenario: Which players play for Grêmio?
    Given the FIFA dataset lists twenty Grêmio players
    When I ask for the club squad
    Then the players and the average rating are returned
    """
    # Given / When
    result = service.club_squad("Grêmio")

    # Then
    assert result["player_count"] == 20
    assert result["average_overall"] == 73.3
    assert all(p["club"] == "Grêmio" for p in result["players"])
    overalls = [p["overall"] for p in result["players"]]
    assert overalls == sorted(overalls, reverse=True)


def test_club_squad_accepts_name_variants(service):
    """Scenario: Club query with a state suffix
    Given users may type "Grêmio-RS" or "Gremio"
    When I ask for the squad
    Then the same Grêmio players are found
    """
    # Given
    variants = ["Grêmio-RS", "Gremio", "Grêmio RS"]

    # When
    results = [service.club_squad(v) for v in variants]

    # Then
    for result in results:
        assert result["player_count"] == 20
        assert {p["name"] for p in result["players"]} == {
            p["name"] for p in results[0]["players"]
        }


def test_forwards_from_a_club(service):
    """Scenario: Show me all forwards from a club
    Given Santos has strikers in the FIFA dataset
    When I filter Santos players by position ST
    Then only strikers are returned
    """
    # Given / When
    result = service.search_players(club="Santos", position="ST", limit=50)

    # Then
    assert result["total"] >= 3
    for player in result["players"]:
        assert player["position"] == "ST"
        assert player["club"] == "Santos"
        assert player["nationality"] == "Brazil"


def test_players_by_rating_band(service):
    """Scenario: Filter by minimum rating
    Given ratings range from the 40s to 94
    When I ask for players rated 90 or higher
    Then every result is rated at least 90
    """
    # Given / When
    result = service.search_players(min_overall=90, limit=100)

    # Then
    assert 5 <= result["total"] <= 20
    assert all(p["overall"] >= 90 for p in result["players"])
    assert result["players"][0]["overall"] == max(
        p["overall"] for p in result["players"]
    )


def test_brazilian_players_by_club(service):
    """Scenario: Brazilian players grouped by club
    Given Brazilians play across hundreds of clubs
    When I ask for the grouped view
    Then clubs are listed with player counts and average ratings
    """
    # Given / When
    result = service.brazilian_players_by_club(limit=10)

    # Then
    assert result["club_count"] == 244
    top_clubs = [row["club"] for row in result["clubs"]]
    assert "Grêmio" in top_clubs
    for row in result["clubs"]:
        assert row["players"] >= 1
        assert row["top_player"]
    counts = [row["players"] for row in result["clubs"]]
    assert counts == sorted(counts, reverse=True)


def test_player_payload_is_serialisable(service):
    """Scenario: Player records serialise cleanly
    Given tools must return JSON-safe values
    When a player is fetched
    Then every field is a JSON primitive
    """
    # Given / When
    player = service.search_players(name="Casemiro")["players"][0]

    # Then
    assert player["name"] == "Casemiro"
    assert player["overall"] == 88
    for value in player.values():
        if isinstance(value, dict):
            assert all(isinstance(v, int) for v in value.values())
        else:
            assert value is None or isinstance(value, (int, str))
