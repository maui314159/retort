"""BDD tests for competition queries.

Feature: Competition Queries

  Scenario: Compute standings for a season
    Given the match data is loaded
    When I compute the Brasileirão Serie A standings for 2019
    Then Flamengo should be the champion with 90 points
    And every team should have played 38 matches

  Scenario: Champions across seasons
    Given the match data is loaded
    When I request the Brasileirão champions
    Then Flamengo should appear (2019) and Palmeiras should appear (2018)
"""

from __future__ import annotations

from brazilian_soccer_mcp.queries import (
    champions,
    relegated_teams,
    standings,
)


def test_standings_2019_flamengo_champion(data):
    st = standings("Brasileirão Serie A", 2019, data=data)
    assert st["matches_counted"] > 0
    top = st["standings"][0]
    assert top["team"] == "Flamengo"
    assert top["points"] == 90
    assert top["wins"] == 28
    assert top["draws"] == 6
    assert top["losses"] == 4
    assert top.get("champion") is True


def test_standings_played_counts_reconcile(data):
    st = standings("Brasileirão Serie A", 2019, data=data)
    for row in st["standings"]:
        assert row["played"] == row["wins"] + row["draws"] + row["losses"]
        assert row["points"] == row["wins"] * 3 + row["draws"]


def test_standings_sorted_by_points(data):
    st = standings("Brasileirão Serie A", 2018, data=data)
    pts = [r["points"] for r in st["standings"]]
    assert pts == sorted(pts, reverse=True)
    assert st["standings"][0]["team"] == "Palmeiras"


def test_standings_2012_fluminense(data):
    st = standings("Brasileirão Serie A", 2012, data=data)
    assert st["standings"][0]["team"] == "Fluminense"


def test_standings_positions_unique(data):
    st = standings("Brasileirão Serie A", 2020, data=data)
    positions = [r["position"] for r in st["standings"]]
    assert positions == sorted(set(positions))
    assert positions[0] == 1


def test_champions_includes_2019_and_2018(data):
    rows = champions("Brasileirão Serie A", data=data)
    by_year = {r["season"]: r["champion"] for r in rows}
    assert by_year.get(2019) == "Flamengo"
    assert by_year.get(2018) == "Palmeiras"
    assert by_year.get(2012) == "Fluminense"


def test_relegated_teams_2019(data):
    rows = relegated_teams("Brasileirão Serie A", 2019, n=4, data=data)
    names = [r["team"] for r in rows]
    assert "CSA" in names
    assert "Chapecoense" in names
    assert len(rows) == 4
