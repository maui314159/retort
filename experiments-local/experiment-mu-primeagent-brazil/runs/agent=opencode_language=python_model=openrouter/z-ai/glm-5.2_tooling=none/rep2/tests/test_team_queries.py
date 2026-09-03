"""BDD tests: team queries and statistics.

Feature: Team Queries
  Scenario: Get team statistics for a season
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season "2019"
    Then I should receive wins, losses, draws and goals

  Scenario: Home-only record
    Given the match data is loaded
    When I request Corinthians' home record in 2022
    Then the away stats should be zero and home stats populated
"""
from __future__ import annotations

from brsl.query_engine import QueryEngine


class TestTeamQueries:
    # Scenario: team statistics for a season
    def test_team_stats_for_season(self, engine: QueryEngine):
        stats = engine.team_stats("Palmeiras", season=2019,
                                  competition="brasileirao")
        assert stats["matches"] > 0
        # Then wins+draws+losses == matches
        assert (stats["wins"] + stats["draws"] + stats["losses"]
                == stats["matches"])
        assert stats["goals_for"] >= 0
        assert stats["goals_against"] >= 0
        assert stats["win_rate"] >= 0

    # Scenario: home-only record
    def test_home_record(self, engine: QueryEngine):
        stats = engine.team_stats("Corinthians", season=2022,
                                  competition="brasileirao", venue="home")
        assert stats["venue"] == "home"
        assert stats["home"]["matches"] > 0
        # When restricted to home, away stats must be zero
        assert stats["away"]["matches"] == 0
        assert stats["matches"] == stats["home"]["matches"]

    # Scenario: away-only record
    def test_away_record(self, engine: QueryEngine):
        stats = engine.team_stats("Flamengo", season=2019,
                                  competition="brasileirao", venue="away")
        assert stats["away"]["matches"] > 0
        assert stats["home"]["matches"] == 0

    # Scenario: competitions participated in
    def test_team_competitions(self, engine: QueryEngine):
        comps = engine.team_competitions("Palmeiras")
        assert len(comps["competitions"]) >= 1
        names = {c["competition"] for c in comps["competitions"]}
        # Palmeiras appears in multiple competition files
        assert any("Brasileirao" in n or "Serie A" in n for n in names)

    # Scenario: disambiguation by state suffix
    def test_atletico_disambiguated_by_state(self, engine: QueryEngine):
        # The 2019 Brasileirao had both Atlético-MG and Athletico-PR; the
        # standings must list them as separate teams.
        table = engine.standings("brasileirao", 2019)
        teams = [row["team"] for row in table["standings"]]
        assert any(t.endswith("-MG") and t.startswith("Atletico") for t in teams)
        assert any(t.endswith("-PR") and t.startswith("Atletico") for t in teams)
        assert len(teams) == 20
