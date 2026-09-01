"""
BDD (Given/When/Then) scenarios for team queries.

Context block
=============
Purpose: validate the team-query capability (TASK.md section "Team Queries"):
per-team statistics, home/away splits, venue filtering and two-team
comparison.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Feature: Team Queries
# ---------------------------------------------------------------------------


def test_team_stats_returns_win_draw_loss(engine):
    """Scenario: Get team statistics for a season.

    Given the match data is loaded
    When I request statistics for "Palmeiras" in season "2022"
    Then I should receive wins, losses, draws, and goals
    And wins + draws + losses should equal matches
    """
    stats = engine.team_stats("Palmeiras", season="2022", competition="Brasileirao")
    assert stats["matches"] > 0
    assert stats["wins"] + stats["draws"] + stats["losses"] == stats["matches"]
    assert stats["goals_for"] >= 0
    assert stats["goals_against"] >= 0
    assert 0.0 <= stats["win_rate"] <= 1.0


def test_team_stats_home_venue_split(engine):
    """Scenario: Home record only.

    Given the match data is loaded
    When I request Corinthians home record for 2022 Brasileirao
    Then every counted match should be a home match
    And the home win/draw/loss counts should sum to matches
    """
    stats = engine.team_stats("Corinthians", season="2022",
                              competition="Brasileirao", venue="home")
    assert stats["venue"] == "home"
    assert stats["home"]["wins"] + stats["home"]["draws"] + stats["home"]["losses"] == stats["matches"]
    # 19 home matches in a 20-team Serie A season.
    assert stats["matches"] == 19


def test_team_stats_state_disambiguation(engine):
    """Scenario: Same-name clubs from different states are not merged.

    Given the match data contains "Atletico-MG" and "Atletico-PR"
    When I request stats for "Atletico-MG" in 2019
    Then the match count should be a single season's worth (<= 50)
    And should not be doubled by merging with Atletico-PR
    """
    stats = engine.team_stats("Atletico-MG", season="2019", competition="Brasileirao")
    assert stats["matches"] <= 50
    assert stats["matches"] > 0


def test_compare_teams_returns_both_stats_and_h2h(engine):
    """Scenario: Compare two teams head-to-head.

    Given the match data is loaded
    When I compare "Palmeiras" and "Santos"
    Then I should receive stats for both teams and a head-to-head record
    """
    result = engine.compare_teams("Palmeiras", "Santos", season="2019")
    assert "team_a_stats" in result
    assert "team_b_stats" in result
    assert "head_to_head" in result
    assert result["team_a_stats"]["matches"] > 0
    assert result["team_b_stats"]["matches"] > 0
