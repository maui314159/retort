"""
BDD (Given/When/Then) scenarios for competition queries.

Context block
=============
Purpose: validate the competition-query capability (TASK.md section
"Competition Queries"): standings calculation, champion detection,
relegation zone and competition metadata.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Feature: Competition Queries
# ---------------------------------------------------------------------------


def test_standings_calculated_from_matches(engine):
    """Scenario: Standings for a competition/season.

    Given the match data is loaded
    When I request the 2019 Brasileirao standings
    Then I should receive a sorted table
    And the first row should be the champion (Flamengo)
    And each row's points should equal 3*wins + draws
    """
    table = engine.standings("Brasileirao", "2019")
    assert len(table) > 0
    # Sorted by points desc.
    points = [r["points"] for r in table]
    assert points == sorted(points, reverse=True)
    assert table[0]["team"] == "Flamengo"
    for r in table:
        assert r["points"] == 3 * r["wins"] + r["draws"]
        assert r["played"] == r["wins"] + r["draws"] + r["losses"]


def test_champion_detection(engine):
    """Scenario: Champion of a competition.

    Given the match data is loaded
    When I request the champion of the 2022 Brasileirao
    Then I should receive the top team of the standings
    """
    champ = engine.champion("Brasileirao", "2022")
    assert champ is not None
    assert champ["champion"] == "Palmeiras"
    assert champ["points"] > 0


def test_relegated_teams_are_bottom(engine):
    """Scenario: Relegation zone.

    Given the match data is loaded
    When I request the bottom 4 teams of the 2019 Brasileirao
    Then I should receive 4 teams
    And they should be the last 4 of the full standings
    """
    full = engine.standings("Brasileirao", "2019")
    relegated = engine.relegated_teams("Brasileirao", "2019", n=4)
    assert len(relegated) == 4
    assert relegated[-1]["position"] == full[-1]["position"]


def test_competition_info_lists_seasons(engine):
    """Scenario: Competition metadata.

    Given the match data is loaded
    When I request info for the Copa do Brasil
    Then I should receive a non-empty seasons list and match count
    """
    info = engine.competition_info("Copa do Brasil")
    assert info["competition"] == "Copa do Brasil"
    assert info["match_count"] > 0
    assert len(info["seasons"]) > 0


def test_all_competitions_summary(engine):
    """Scenario: Summary of all competitions.

    Given the match data is loaded
    When I request a summary of all competitions
    Then I should receive multiple competitions including Brasileirao
    """
    summary = engine.competition_info()
    assert "Brasileirao" in summary
    assert summary["Brasileirao"]["matches"] > 0
