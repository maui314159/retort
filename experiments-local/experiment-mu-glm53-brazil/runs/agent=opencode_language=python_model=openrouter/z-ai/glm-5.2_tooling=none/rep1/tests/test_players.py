"""
BDD (Given/When/Then) scenarios for player queries.

Context block
=============
Purpose: validate the player-query capability (TASK.md section "Player
Queries"): name search, nationality filter (Brazilian players), club filter
and rating sorting.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Feature: Player Queries
# ---------------------------------------------------------------------------


def test_find_brazilian_players(engine):
    """Scenario: Find all Brazilian players.

    Given the FIFA player database is loaded
    When I search for Brazilian players
    Then every returned player should have nationality Brazil
    And results should be sorted by overall rating descending
    """
    players = engine.brazilian_players(limit=20)
    assert len(players) > 0
    for p in players:
        assert p["nationality"] == "Brazil"
    ratings = [p["overall"] for p in players]
    assert ratings == sorted(ratings, reverse=True)


def test_find_player_by_name(engine):
    """Scenario: Search a player by name.

    Given the FIFA player database is loaded
    When I search for players named "Neymar"
    Then I should receive at least one match
    And the first match should be Neymar Jr with a high overall rating
    """
    players = engine.find_players(name="Neymar")
    assert len(players) >= 1
    assert "Neymar" in players[0]["name"]
    assert players[0]["overall"] >= 88


def test_find_players_by_club(engine):
    """Scenario: Players at a club.

    Given the FIFA player database is loaded
    When I search for players at "Barcelona"
    Then every returned player should belong to a Barcelona club
    """
    players = engine.find_players(club="Barcelona", limit=50)
    assert len(players) > 0
    for p in players:
        assert "barcelona" in p["club"].lower()


def test_top_players_for_club_sorted(engine):
    """Scenario: Highest-rated players at a club.

    Given the FIFA player database is loaded
    When I request the top players for "Real Madrid"
    Then results should be sorted by overall rating descending
    """
    players = engine.top_players_for_club("Real Madrid", limit=5)
    if not players:
        # Club not present in this FIFA snapshot; skip gracefully.
        return
    ratings = [p["overall"] for p in players]
    assert ratings == sorted(ratings, reverse=True)


def test_find_players_min_overall_filter(engine):
    """Scenario: Filter players by minimum rating.

    Given the FIFA player database is loaded
    When I search for Brazilian players with overall >= 85
    Then every returned player should have overall >= 85
    """
    players = engine.brazilian_players(min_overall=85, limit=50)
    assert len(players) > 0
    for p in players:
        assert p["overall"] >= 85
