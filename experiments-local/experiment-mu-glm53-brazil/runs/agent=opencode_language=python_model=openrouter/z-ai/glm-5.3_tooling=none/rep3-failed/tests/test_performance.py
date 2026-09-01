"""BDD scenarios for query performance budgets.

Feature: Query Performance
  TASK.md requires simple lookups under 2 seconds and aggregate queries
  under 5 seconds.
"""

from __future__ import annotations

import time

import pytest

pytestmark = pytest.mark.performance


class TestLatencyBudgets:
    """
    Scenario: Queries answer within the TASK.md time budgets
      Given the datasets are loaded
      When I run simple lookups and aggregate queries
      Then lookups finish in under 2 seconds and aggregates in under 5
    """

    def test_when_running_a_simple_lookup_then_it_takes_under_two_seconds(self, engine):
        start = time.perf_counter()
        result = engine.search_matches(team="Flamengo", opponent="Fluminense", limit=20)
        elapsed = time.perf_counter() - start
        assert result.total > 0
        assert elapsed < 2.0

    def test_when_running_a_player_lookup_then_it_takes_under_two_seconds(self, engine):
        start = time.perf_counter()
        players = engine.search_players(nationality="Brazil", limit=20)
        elapsed = time.perf_counter() - start
        assert players
        assert elapsed < 2.0

    def test_when_calculating_standings_then_it_takes_under_five_seconds(self, engine):
        start = time.perf_counter()
        for season in range(2003, 2024):
            engine.standings(season)
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0

    def test_when_aggregating_statistics_then_it_takes_under_five_seconds(self, engine):
        start = time.perf_counter()
        stats = engine.statistics(competition="Brasileirão")
        elapsed = time.perf_counter() - start
        assert stats.matches > 10_000
        assert elapsed < 5.0


class TestColdLoadBudget:
    """
    Scenario: The server loads all six datasets quickly
      Given a fresh process
      When the datasets load
      Then startup completes in well under 30 seconds
    """

    def test_when_loading_all_datasets_then_startup_is_quick(self, data_dir):
        from brazilian_soccer_mcp.loader import load_data

        start = time.perf_counter()
        data = load_data(data_dir)
        elapsed = time.perf_counter() - start
        assert len(data.matches) == 23_954
        assert len(data.players) == 18_207
        assert elapsed < 30.0
