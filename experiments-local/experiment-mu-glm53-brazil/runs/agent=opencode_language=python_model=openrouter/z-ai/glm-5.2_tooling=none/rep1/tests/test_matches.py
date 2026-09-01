"""
BDD (Given/When/Then) scenarios for match queries.

Context block
=============
Purpose: validate the match-query capability of the MCP server as specified
in TASK.md (section "Match Queries"). Scenarios cover finding matches by
team, by opponent pair, by competition, by season and by date range, plus
the head-to-head aggregate record.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Feature: Match Queries
# ---------------------------------------------------------------------------


def test_find_matches_between_two_teams(engine):
    """Scenario: Find matches between two teams.

    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition
    """
    # When
    matches = engine.find_matches(team="Flamengo", opponent="Fluminense")

    # Then
    assert isinstance(matches, list)
    assert len(matches) > 0
    for m in matches:
        assert "date" in m
        assert "home_goal" in m and "away_goal" in m
        assert "competition" in m
        teams = {m["home_team"], m["away_team"]}
        assert "Flamengo" in teams or "Fluminense" in teams


def test_find_matches_by_team_and_season(engine):
    """Scenario: Find matches for a team in a season.

    Given the match data is loaded
    When I search for Palmeiras matches in season 2022
    Then every returned match should involve Palmeiras and have season 2022
    """
    matches = engine.find_matches(team="Palmeiras", season="2022")
    assert len(matches) > 0
    for m in matches:
        assert m["home_team"] == "Palmeiras" or m["away_team"] == "Palmeiras"
        assert m["season"] == "2022"


def test_find_matches_by_competition(engine):
    """Scenario: Find matches by competition.

    Given the match data is loaded
    When I search for Copa Libertadores matches in 2019
    Then every returned match should belong to the Copa Libertadores
    """
    matches = engine.find_matches(competition="Copa Libertadores", season="2019", limit=20)
    assert len(matches) > 0
    for m in matches:
        assert m["competition"] == "Copa Libertadores"
        assert m["season"] == "2019"


def test_find_matches_by_date_range(engine):
    """Scenario: Find matches by date range.

    Given the match data is loaded
    When I search for matches between 2019-01-01 and 2019-12-31
    Then every returned match date should fall within 2019
    """
    matches = engine.find_matches(date_from="2019-01-01", date_to="2019-12-31", limit=50)
    assert len(matches) > 0
    for m in matches:
        assert m["date"].startswith("2019")


def test_head_to_head_returns_aggregate_record(engine):
    """Scenario: Head-to-head record between two teams.

    Given the match data is loaded
    When I request the head-to-head record of Flamengo vs Fluminense
    Then I should receive wins, draws, losses and a match list
    And the sum of wins and draws should equal the match count
    """
    h2h = engine.head_to_head("Flamengo", "Fluminense")
    assert h2h["matches"] > 0
    assert h2h["team_a_wins"] + h2h["team_b_wins"] + h2h["draws"] == h2h["matches"]
    assert len(h2h["match_list"]) == h2h["matches"]


def test_team_name_normalization_handles_state_suffix(engine):
    """Scenario: Team name variations resolve to the same team.

    Given the match data is loaded with "Palmeiras-SP" style names
    When I search for "Palmeiras-SP" and separately for "Palmeiras"
    Then both queries should return the same set of matches
    """
    a = engine.find_matches(team="Palmeiras-SP", season="2019")
    b = engine.find_matches(team="Palmeiras", season="2019")
    assert a == b
    assert len(a) > 0
