"""BDD tests for player queries.

Feature: Player Queries

  Scenario: Search the FIFA player database
    Given the FIFA player data is loaded
    When I search for Brazilian players with overall >= 85
    Then I should receive players all of nationality Brazil and overall >= 85

  Scenario: Top Brazilian players
    Given the FIFA player data is loaded
    When I request the top Brazilian players
    Then the first result should be Neymar Jr with overall 92

  Scenario: Players for a Brazilian club
    Given the FIFA player data is loaded
    When I request the players for "Santos"
    Then I should receive a non-empty roster with an average rating
"""

from __future__ import annotations

from brazilian_soccer_mcp.queries import (
    players_for_club,
    search_players,
    top_brazilian_players,
    top_clubs_by_nationality,
)


def test_search_brazilian_players(data):
    rows = search_players(nationality="Brazil", min_overall=85, limit=50, data=data)
    assert rows, "expected some Brazilian players rated >= 85"
    for r in rows:
        assert "brazil" in r["nationality"].lower()
        assert r["overall"] >= 85


def test_search_players_by_name(data):
    rows = search_players(name="Neymar", data=data)
    assert rows
    assert any("neymar" in r["name"].lower() for r in rows)


def test_search_players_by_position(data):
    rows = search_players(position="ST", min_overall=85, limit=50, data=data)
    assert rows
    for r in rows:
        assert r["position"]


def test_top_brazilian_players(data):
    rows = top_brazilian_players(limit=10, data=data)
    assert rows
    assert rows[0]["name"] == "Neymar Jr"
    assert rows[0]["overall"] == 92
    overalls = [r["overall"] for r in rows]
    assert overalls == sorted(overalls, reverse=True)


def test_top_brazilian_players_all_brazilian(data):
    rows = top_brazilian_players(limit=20, data=data)
    assert all("brazil" in r["nationality"].lower() for r in rows)


def test_players_for_club_santos(data):
    r = players_for_club("Santos", data=data)
    assert r["player_count"] > 0
    assert r["average_rating"] is not None
    assert all(p["club"] for p in r["players"])


def test_players_for_club_handles_name_variants(data):
    a = players_for_club("Santos", data=data)
    b = players_for_club("Santos FC", data=data)
    assert a["player_count"] == b["player_count"]


def test_top_clubs_by_brazilian_nationality(data):
    rows = top_clubs_by_nationality("Brazil", limit=10, data=data)
    assert rows
    assert rows[0]["player_count"] >= rows[-1]["player_count"]
    for r in rows:
        assert r["player_count"] > 0
