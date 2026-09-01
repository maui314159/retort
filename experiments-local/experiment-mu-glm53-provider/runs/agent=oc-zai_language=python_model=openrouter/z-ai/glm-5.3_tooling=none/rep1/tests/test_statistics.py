"""
BDD scenarios: statistical analysis (TASK.md "Required Capabilities" #5).

Feature: Statistical Analysis
  Scenario: Average goals per match
    Given the match data is loaded
    When I request aggregate stats for the Brasileirão
    Then I should receive the average goals and home/away win rates
"""

from __future__ import annotations

import pytest


class TestCompetitionStats:
    """Scenario: average goals per match + home advantage."""

    def test_brasileirao_all_time(self, service):
        # Given the match data is loaded
        # When I request Brasileirão aggregates
        stats = service.competition_stats("brasileirao")
        # Then the numbers match the dataset ground truth
        assert stats.matches == 8518
        assert stats.avg_goals == 2.57
        assert stats.home_win_rate == 49.7
        assert stats.draw_rate == 26.5
        assert stats.away_win_rate == 23.9

    def test_rates_sum_to_100(self, service):
        stats = service.competition_stats("brasileirao")
        assert (
            stats.home_wins + stats.draws + stats.away_wins == stats.matches
        )

    def test_single_season_stats(self, service):
        stats = service.competition_stats("brasileirao", 2019)
        assert stats.matches == 380
        # 2019 was a higher-scoring season than the all-time average
        assert stats.avg_goals == 2.31

    def test_libertadores_stats(self, service):
        stats = service.competition_stats("libertadores")
        assert stats.matches == 1253
        assert stats.avg_goals == 2.55

    def test_formatting(self, service):
        from brazilian_soccer_mcp.formatting import format_competition_stats

        text = format_competition_stats(service.competition_stats("brasileirao"))
        assert "Average goals per match: 2.57" in text
        assert "Home win rate: 49.7%" in text


class TestBiggestWins:
    """Scenario: 'Show me the biggest wins in the dataset'."""

    def test_biggest_overall(self, service):
        wins = service.biggest_wins(limit=3)
        # Then the record victory is São Paulo 9-1 4 de Julho (Copa do Brasil)
        top = wins[0]
        assert top.home_display == "São Paulo"
        assert top.score_str() == "9-1"
        assert top.competition == "Copa do Brasil"
        # And the list is sorted by decreasing margin
        margins = [m.margin() for m in wins]
        assert margins == sorted(margins, reverse=True)

    def test_biggest_per_competition(self, service):
        wins = service.biggest_wins(competition="libertadores", limit=2)
        assert all(m.competition == "Copa Libertadores" for m in wins)
        assert wins[0].score_str() == "8-0"

    def test_biggest_in_season(self, service):
        wins = service.biggest_wins(competition="brasileirao", season=2019, limit=1)
        # 2019's biggest league win: Flamengo 6-1 Goiás? - margin 5
        assert wins[0].margin() == 5

    def test_formatting(self, service):
        from brazilian_soccer_mcp.formatting import format_biggest_wins

        text = format_biggest_wins(service.biggest_wins(limit=2), scope="test")
        assert text.startswith("Biggest victories test:")
        assert "São Paulo 9-1" in text


class TestBestRecords:
    """Scenario: 'Which team has the best home/away record?'."""

    def test_best_away_all_time(self, service):
        records = service.best_records(venue="away", min_matches=50, limit=3)
        # Then Flamengo leads the all-time away table
        assert records[0].display == "Flamengo"
        assert records[0].matches > 400
        # And records respect the minimum-match threshold
        assert all(r.matches >= 50 for r in records)

    def test_best_home_season(self, service):
        records = service.best_records(
            venue="home", competition="brasileirao", season=2019, min_matches=19, limit=3
        )
        assert all(r.matches == 19 for r in records)
        # 2019's best home record: Flamengo (16 wins at Maracanã)
        assert records[0].display == "Flamengo"

    def test_win_rate_ordering(self, service):
        records = service.best_records(venue="home", min_matches=30, limit=10)
        rates = [r.win_rate for r in records]
        assert rates == sorted(rates, reverse=True)

    def test_invalid_venue(self, service):
        with pytest.raises(ValueError):
            service.best_records(venue="both")


class TestDerbies:
    """Scenario: 'Show me all derbies in 2023'."""

    def test_derbies_2023(self, service):
        derbies = service.derby_matches(season=2023)
        # Then classic fixtures are detected with their names
        assert len(derbies) == 29
        names = {name for name, _ in derbies}
        assert "Fla-Flu" in names
        assert "Grenal" in names
        assert "Majestoso" in names

    def test_derby_pairs_only(self, service):
        derbies = service.derby_matches(season=2023)
        from brazilian_soccer_mcp.normalizer import DERBIES

        known = {frozenset((a, b)) for a, b, _ in DERBIES}
        for _, match in derbies:
            assert frozenset((match.home_id, match.away_id)) in known

    def test_derby_competition_filter(self, service):
        derbies = service.derby_matches(season=2023, competition="Copa do Brasil")
        for _, match in derbies:
            assert match.competition == "Copa do Brasil"


class TestCompareSeasons:
    """Scenario: 'Compare the 2018 and 2019 seasons'."""

    def test_comparison_output(self, service):
        text = service.compare_seasons("brasileirao", 2018, 2019)
        # Then both seasons' aggregates are reported side by side
        assert "Brasileirão Série A 2018 vs 2019" in text
        assert "Average goals/match: 2.18 vs 2.31" in text
        assert "Champion: Palmeiras (80 pts) vs Flamengo (90 pts)" in text

    def test_home_advantage_shift(self, service):
        # Given 2019 saw a big rise in away wins vs 2018
        stats_18 = service.competition_stats("brasileirao", 2018)
        stats_19 = service.competition_stats("brasileirao", 2019)
        # Then the shift is visible in the aggregates
        assert stats_19.away_win_rate > stats_18.away_win_rate


class TestPerformance:
    """Scenario: TASK.md query performance budget."""

    def test_simple_lookup_under_2s(self, service):
        import time

        # Given a simple lookup (spec: < 2 seconds)
        start = time.perf_counter()
        service.search_matches(team="Flamengo", opponent="Fluminense")
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0

    def test_aggregate_query_under_5s(self, service):
        import time

        # Given aggregate queries (spec: < 5 seconds)
        start = time.perf_counter()
        service.competition_stats("brasileirao")
        service.standings("brasileirao", 2019)
        service.best_records(venue="away", min_matches=10)
        service.biggest_wins()
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0

    def test_cold_load_and_query_under_budget(self):
        import time

        from brazilian_soccer_mcp.loaders import load_all
        from brazilian_soccer_mcp.service import SoccerService
        from tests.conftest import DATA_DIR

        # Given a cold start: one-time CSV load (~0.8 s raw) plus a simple
        # lookup. The spec's < 2 s budget applies to lookups on a running
        # server (see test_simple_lookup_under_2s); the cold path includes
        # the one-off data load, so it gets the < 5 s aggregate budget.
        # (Coverage instrumentation roughly doubles load time.)
        start = time.perf_counter()
        fresh = SoccerService(load_all(DATA_DIR))
        fresh.search_matches(team="Palmeiras", season=2023)
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0
