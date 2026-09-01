"""BDD scenarios for statistical analysis (TASK.md "Statistical Analysis").

Feature: Statistical Analysis
  Scenario: Aggregate statistics
    Given the match data is loaded
    When I request average goals per match for a competition
    Then I should receive the average and result distribution
"""

from __future__ import annotations

from data_loader import SERIE_A
from server import (
    get_aggregate_statistics,
    get_biggest_wins,
    get_derby_matches,
)
from stats import biggest_wins, competition_aggregates


class TestAggregateStatistics:
    """Gherkin: 'What's the average goals per match in the Brasileirão?'"""

    def test_average_goals_per_match(self, data):
        """
        Scenario: league-wide average
          Given the Brasileirão dataset
          When I request aggregate statistics
          Then the average goals per match is around 2.5
        """
        result = get_aggregate_statistics(competition="Brasileirão")
        agg = result["data"]
        assert agg["matches"] > 8000
        assert 2.2 <= agg["avg_goals_per_match"] <= 2.8

    def test_result_distribution_sums_to_100(self, data):
        """
        Scenario: home/draw/away distribution
          Given any competition
          When aggregate statistics are computed
          Then home + draw + away win rates sum to ~100%
        """
        result = get_aggregate_statistics(competition="Libertadores")
        agg = result["data"]
        total = agg["home_win_rate_pct"] + agg["draw_rate_pct"] + agg["away_win_rate_pct"]
        assert abs(total - 100.0) < 0.2
        assert agg["home_win_rate_pct"] > agg["away_win_rate_pct"]

    def test_per_season_breakdown(self, data):
        """
        Scenario: season-by-season comparison
          Given the Brasileirão
          When aggregate statistics are requested without a season
          Then a per-season breakdown is included
        """
        result = get_aggregate_statistics(competition="Brasileirão")
        per_season = result["data"]["per_season"]
        assert len(per_season) >= 20
        assert {row["season"] for row in per_season} >= {2019, 2020, 2021}

    def test_home_advantage_is_real(self, data):
        """
        Scenario: home vs away performance
          Given all Brasileirão matches
          When result rates are computed
          Then home teams win more often than away teams
        """
        agg = competition_aggregates(data.matches_by_competition(SERIE_A))
        assert agg["home_win_rate_pct"] > 45
        assert agg["away_win_rate_pct"] < 30


class TestBiggestWins:
    """Gherkin: 'Show me the biggest wins in the dataset'."""

    def test_biggest_wins_are_ranked_by_margin(self, data):
        """
        Scenario: ranking by goal margin
          Given all matches
          When I request the biggest wins
          Then results are ordered by descending margin
        """
        result = get_biggest_wins(limit=10)
        margins = [w["margin"] for w in result["data"]["wins"]]
        assert margins == sorted(margins, reverse=True)
        assert margins[0] >= 7

    def test_biggest_win_has_competition_and_date(self, data):
        """
        Scenario: informative output
          Given the biggest wins
          When they are returned
          Then each includes date, score, competition and margin
        """
        result = get_biggest_wins(limit=5)
        for win in result["data"]["wins"]:
            assert win["date"]
            assert win["competition"]
            assert "-" in win["score"]
            assert isinstance(win["margin"], int)

    def test_biggest_wins_filtered_by_team(self, data):
        """
        Scenario: team-filtered biggest wins
          Given Palmeiras matches
          When I request their biggest wins
          Then every win involves Palmeiras
        """
        result = get_biggest_wins(team="Palmeiras", limit=5)
        assert result["data"]["wins"]
        display_teams = {w["home_team"] for w in result["data"]["wins"]} | {
            w["away_team"] for w in result["data"]["wins"]
        }
        assert "Palmeiras" in display_teams

    def test_knowledge_level_margin_exists(self, data):
        """
        Scenario: known result present
          Given River Plate's 8-0 wins in the Libertadores
          When the biggest wins are computed
          Then an 8-goal margin appears
        """
        wins = biggest_wins(data.matches_by_competition("Copa Libertadores"), limit=5)
        assert wins[0]["margin"] == 8


class TestDerbyMatches:
    """Gherkin: 'Show me all derbies in 2023'."""

    def test_derbies_in_2023(self, data):
        """
        Scenario: derby matches by season
          Given the 2023 season
          When I request derby matches
          Then only classic rival pairings are returned
        """
        result = get_derby_matches(season=2023)
        matches = result["data"]["matches"]
        assert matches
        known = set(result["data"]["derbies_known"])
        assert all(d["derby"] in known for d in matches)
        assert all(d["season"] == 2023 for d in matches)

    def test_fla_flu_derby(self, data):
        """
        Scenario: Fla-Flu
          Given the Fla-Flu rivalry
          When I request its matches
          Then Flamengo and Fluminense meetings are returned
        """
        result = get_derby_matches(derby="Fla-Flu", season=2019)
        matches = result["data"]["matches"]
        assert matches
        for d in matches:
            assert d["derby"] == "Fla-Flu"
            teams = {d["home_team"], d["away_team"]}
            assert teams == {"Flamengo", "Fluminense"}

    def test_gre_nal_2019(self, data):
        """
        Scenario: Gre-Nal
          Given the 2019 Gre-Nal meetings
          When I request them
          Then two Série A matches between Grêmio and Internacional are
            returned
        """
        result = get_derby_matches(derby="Gre-Nal", season=2019)
        assert len(result["data"]["matches"]) == 2
        for d in result["data"]["matches"]:
            assert {d["home_team"], d["away_team"]} == {"Grêmio", "Internacional"}
