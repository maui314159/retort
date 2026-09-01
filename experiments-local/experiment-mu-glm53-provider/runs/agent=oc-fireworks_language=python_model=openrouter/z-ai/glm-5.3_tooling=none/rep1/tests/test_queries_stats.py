"""
Feature: Statistical Analysis
  As a soccer fan I want aggregate statistics - goals per match, home
  advantage, biggest wins, derby listings - computed across the whole
  knowledge graph.
"""

from __future__ import annotations

from brazilian_soccer_mcp.queries import (
    biggest_wins,
    competition_stats,
    derbies,
)


class TestAggregateStatistics:
    """TASK.md: "What's the average goals per match in the Brasileirão?"."""

    def test_average_goals_serie_a_2019(self, ds):
        """
        Scenario: average goals for one season
          Given the match data is loaded
          When I request Série A 2019 statistics
          Then the averages cover all 380 played matches
          And average goals per match is 2.31
          And the three result rates sum to 100%
        """
        result = competition_stats(ds, competition="serie_a", season=2019)
        assert result["ok"], result
        stats = result["stats"]
        assert stats["played"] == 380
        assert stats["avg_goals_per_match"] == 2.31
        assert stats["home_win_rate"] == 48.4
        assert (
            round(
                stats["home_win_rate"] + stats["draw_rate"] + stats["away_win_rate"], 1
            )
            == 100.0
        )

    def test_average_goals_all_serie_a(self, ds):
        """
        Scenario: the all-time Série A picture
          Given the match data is loaded
          When I request Série A statistics with no season
          Then averages cover every played league match since 2003
          And home teams win roughly half the matches
        """
        result = competition_stats(ds, competition="serie_a")
        assert result["ok"]
        stats = result["stats"]
        assert stats["played"] == 8402
        assert 2.3 < stats["avg_goals_per_match"] < 2.8
        assert 45 < stats["home_win_rate"] < 55
        assert stats["avg_home_goals"] > stats["avg_away_goals"]

    def test_stats_across_every_competition(self, ds):
        """
        Scenario: one overview for all competitions
          Given the match data is loaded
          When I request statistics with no competition filter
          Then an overall block plus a per-competition breakdown is returned
        """
        result = competition_stats(ds)
        assert result["ok"]
        assert result["competition"] == "all competitions"
        assert result["stats"]["played"] > 15_000
        assert len(result["by_competition"]) == 5
        for entry in result["by_competition"]:
            assert entry["played"] > 500

    def test_stats_ignore_unplayed(self, ds):
        """
        Scenario: unplayed fixtures never skew averages
          Given the match data is loaded
          When I request Libertadores 2015 statistics
            (one abandoned Boca/River fixture has no score)
          Then only played matches are averaged
        """
        result = competition_stats(ds, competition="libertadores", season=2015)
        assert result["ok"]
        assert result["stats"]["not_played"] == 1
        assert result["stats"]["played"] == 125


class TestBiggestWins:
    """TASK.md: "Show me the biggest wins in the dataset"."""

    def test_biggest_overall(self, ds):
        """
        Scenario: the largest victory margins in the data
          Given the match data is loaded
          When I request the biggest wins across all competitions
          Then the top match is São Paulo 9-1 4 de Julho (Copa do Brasil 2021)
          And every row carries a margin
        """
        result = biggest_wins(ds, limit=10)
        assert result["ok"], result
        top = result["biggest_wins"][0]
        assert top["home"] == "São Paulo"
        assert top["score"] == "9-1"
        assert top["away"].startswith("4 de Julho")
        assert top["competition"] == "copa_do_brasil"
        assert top["margin"] == 8
        margins = [m["margin"] for m in result["biggest_wins"]]
        assert margins == sorted(margins, reverse=True)

    def test_biggest_libertadores_rout(self, ds):
        """
        Scenario: the biggest Libertadores win
          Given the match data is loaded
          When I request the biggest Libertadores wins
          Then River Plate 8-0 appears (Jorge Wilstermann, 2017)
        """
        result = biggest_wins(ds, competition="libertadores", limit=5)
        assert result["ok"]
        assert result["biggest_wins"][0]["home"] == "River Plate"
        assert result["biggest_wins"][0]["score"] == "8-0"
        assert result["biggest_wins"][0]["margin"] == 8

    def test_biggest_in_one_season(self, ds):
        """
        Scenario: biggest wins scoped to a season
          Given the match data is loaded
          When I request the biggest 2019 wins
          Then every result is from 2019
        """
        result = biggest_wins(ds, season=2019, limit=5)
        assert result["ok"]
        assert all(m["season"] == 2019 for m in result["biggest_wins"])
        assert result["biggest_wins"][0]["margin"] >= 5


class TestDerbies:
    """TASK.md: "Show me all derbies in 2023"."""

    def test_derbies_in_2023(self, ds):
        """
        Scenario: classic derbies of one season
          Given the match data is loaded
          When I request derbies for 2023
          Then several derbies have fixtures that season
          And Fla-Flu met four times (two league legs, two cup legs)
        """
        result = derbies(ds, season=2023)
        assert result["ok"], result
        assert result["derbies_with_matches"] == 10
        fla_flu = next(d for d in result["derbies"] if d["derby"] == "Fla-Flu")
        assert fla_flu["matches_in_scope"] == 4
        assert {fla_flu["team_a"], fla_flu["team_b"]} == {"Flamengo", "Fluminense"}

    def test_derby_all_time_records(self, ds):
        """
        Scenario: all-time derby head-to-head
          Given the match data is loaded
          When I request derbies with no season
          Then every curated derby reports an all-time W-D-W record
        """
        result = derbies(ds)
        assert result["ok"]
        assert len(result["derbies"]) >= 12
        for derby in result["derbies"]:
            record = derby["all_time"]
            assert (
                record["meetings"]
                == record["wins_team_a"] + record["wins_team_b"] + record["draws"]
            )
            assert record["meetings"] > 0

    def test_gre_nal_and_ba_vi_present(self, ds):
        """
        Scenario: the derby catalogue covers the famous rivalries
          Given the derby catalogue
          Then Gre-Nal (Grêmio x Internacional) and Ba-Vi (Bahia x Vitória)
            are both listed with matches
        """
        result = derbies(ds)
        names = {d["derby"]: d for d in result["derbies"]}
        assert "Gre-Nal" in names
        assert {names["Gre-Nal"]["team_a"], names["Gre-Nal"]["team_b"]} == {
            "Grêmio",
            "Internacional",
        }
        assert "Ba-Vi" in names
        assert names["Ba-Vi"]["all_time"]["meetings"] > 10
