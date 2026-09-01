"""
BDD GWT scenarios: statistical analysis and query performance.

Gherkin counterpart: ``tests/features/statistics.feature``.

Covers TASK.md "Required Capabilities" -> "5. Statistical Analysis"
(averages, trends, home vs away, biggest wins) and "Success Criteria" ->
"Query Performance" (<2s simple lookups, <5s aggregate queries).
"""

from __future__ import annotations

import time

import pytest

from brazilian_soccer_mcp import service as svc


class TestSeasonAverages:
    def test_given_serie_a_2019_when_averaged_then_goals_per_match(self, dataset):
        # Given "What's the average goals per match in the Brasileirão?"
        # When averaging the 2019 season
        avgs = svc.season_averages(dataset, "Brasileirão Serie A", 2019)
        # Then 380 matches produced 876 goals (2.31 per match)
        assert avgs["matches"] == 380
        assert avgs["total_goals"] == 876
        assert avgs["average_goals_per_match"] == 2.31

    def test_given_2019_when_averaged_then_home_advantage_visible(self, dataset):
        # Given home teams win more often in Brazil
        avgs = svc.season_averages(dataset, "Brasileirão Serie A", 2019)
        # Then home win rate dominates and rates sum to 100
        assert avgs["home_win_rate"] > avgs["away_win_rate"]
        assert avgs["home_win_rate"] + avgs["draw_rate"] + avgs["away_win_rate"] == 100.0
        assert avgs["average_home_goals"] > avgs["average_away_goals"]

    def test_given_whole_history_when_averaged_then_all_seasons_pooled(self, dataset):
        # Given no season filter
        avgs = svc.season_averages(dataset, "Copa Libertadores")
        # Then every scored Libertadores match is pooled
        # (2 unscored rows excluded: the abandoned 2015 Boca x River
        # Superclásico and the scoreless 2022 final row)
        assert avgs["matches"] == 1253

    def test_given_an_unknown_competition_when_averaged_then_error(self, dataset):
        with pytest.raises(ValueError, match="Unknown competition"):
            svc.season_averages(dataset, "Premier League")


class TestBiggestWins:
    def test_given_the_dataset_when_ranking_then_margin_sorted(self, dataset):
        # Given "Show me the biggest wins in the dataset"
        # When ranking by margin
        result = svc.biggest_wins(dataset, limit=5)
        # Then margins are non-increasing
        margins = [m["margin"] for m in result["matches"]]
        assert margins == sorted(margins, reverse=True)
        assert margins[0] == 8

    def test_given_biggest_wins_then_each_has_full_context(self, dataset):
        # Given the ranked wins
        result = svc.biggest_wins(dataset, limit=3)
        # Then each entry identifies the fixture
        for m in result["matches"]:
            assert m["date"] and m["home_team"] and m["away_team"]
            assert m["competition"] and m["margin"] >= 1

    def test_given_serie_a_filter_when_ranking_then_league_only(self, dataset):
        # Given Brasileirão-only ranking
        result = svc.biggest_wins(dataset, competition="Brasileirão Serie A", limit=3)
        # Then only Serie A matches appear, led by 7-goal margins
        assert all(m["competition"] == "Brasileirão Serie A" for m in result["matches"])
        assert m_margin(result["matches"][0]) == 7

    def test_given_a_season_when_ranking_then_restricted(self, dataset):
        result = svc.biggest_wins(dataset, competition="Brasileirão Serie A", season=2019, limit=5)
        assert all(m["season"] == 2019 for m in result["matches"])


def m_margin(match: dict) -> int:
    return match["margin"]


class TestMatchStatistics:
    def test_given_flamengo_2023_when_stats_requested_then_extended_fields(self, dataset):
        # Given "corner and shot statistics" questions
        # When requesting extended statistics
        result = svc.match_statistics(dataset, team="Flamengo", season=2023, limit=3)
        # Then matches carry corners/shots/attacks and half-time labels
        assert result["total_matches"] == 48
        stats = result["matches"][0]["statistics"]
        assert stats is not None
        assert "-" in stats["corners"]
        assert stats["half_time"] in {"WON", "LOST", "DRAW", None}

    def test_given_statistics_when_filtered_then_opponent_respected(self, dataset):
        # Given a specific pairing
        result = svc.match_statistics(dataset, team="Flamengo", opponent="Fluminense")
        # Then only head-to-head fixtures are returned
        assert result["total_matches"] > 0
        for m in result["matches"]:
            teams = {m["home_team"], m["away_team"]}
            assert "Flamengo" in teams and "Fluminense" in teams


class TestPerformance:
    def test_given_warm_dataset_when_simple_lookup_then_under_2s(self, dataset):
        # Given the in-memory dataset (TASK.md: simple lookups < 2 seconds)
        # When running a team search
        start = time.monotonic()
        svc.search_matches(dataset, team="Flamengo", opponent="Fluminense")
        # Then it completes within the budget
        assert time.monotonic() - start < 2.0

    def test_given_warm_dataset_when_aggregate_query_then_under_5s(self, dataset):
        # Given TASK.md: aggregate queries < 5 seconds
        # When running heavy aggregates (standings + full player scan)
        start = time.monotonic()
        svc.standings(dataset, "Brasileirão Serie A", 2019)
        svc.head_to_head(dataset, "Palmeiras", "Santos")
        svc.find_players(dataset, nationality="Brazil")
        svc.competition_info(dataset, "Brasileirão Serie A")
        # Then everything completes within the budget
        assert time.monotonic() - start < 5.0
