"""BDD tests: statistical analysis.

Feature: Statistical Analysis
  Scenario: Average goals per match
    Given the match data is loaded
    When I request the average goals for the Brasileirao in 2019
    Then I should receive a positive average and home/draw/away win rates
    And the three win rates should sum to 100
"""
from __future__ import annotations

from brsl.query_engine import QueryEngine


class TestStatistics:
    # Scenario: average goals per match
    def test_average_goals(self, engine: QueryEngine):
        agg = engine.average_goals("brasileirao", 2019)
        assert agg["matches"] == 380
        assert 0 < agg["avg_goals"] < 10
        total_rate = (agg["home_win_rate"] + agg["draw_rate"]
                      + agg["away_win_rate"])
        assert round(total_rate, 1) == 100.0

    # Scenario: home advantage
    def test_home_advantage(self, engine: QueryEngine):
        agg = engine.average_goals("brasileirao", 2019)
        # Home teams should win more often than away teams.
        assert agg["home_win_rate"] > agg["away_win_rate"]

    # Scenario: biggest victories
    def test_biggest_victories(self, engine: QueryEngine):
        bv = engine.biggest_victories(limit=5)
        assert len(bv["biggest_victories"]) == 5
        margins = [v["winner_goals"] - v["loser_goals"]
                   for v in bv["biggest_victories"]]
        assert margins == sorted(margins, reverse=True)
        assert margins[0] >= margins[-1]

    def test_biggest_victories_libertadores(self, engine: QueryEngine):
        bv = engine.biggest_victories("libertadores", limit=3)
        assert len(bv["biggest_victories"]) == 3
        for v in bv["biggest_victories"]:
            assert v["competition"] == "Copa Libertadores"

    # Scenario: top scoring teams
    def test_top_scoring_teams(self, engine: QueryEngine):
        top = engine.top_scoring_teams(season=2019, competition="brasileirao",
                                       limit=5)
        assert len(top["teams"]) == 5
        goals = [t["goals"] for t in top["teams"]]
        assert goals == sorted(goals, reverse=True)

    # Scenario: home vs away breakdown equals average_goals output
    def test_home_vs_away_alias(self, engine: QueryEngine):
        a = engine.average_goals("brasileirao", 2019)
        b = engine.home_vs_away("brasileirao", 2019)
        assert a == b
