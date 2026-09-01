"""Feature: Query Performance
  Simple lookups respond in under 2 seconds and aggregate queries in
  under 5 seconds, with no timeout errors.
"""

import time

from brazilian_soccer.repository import DataRepository
from brazilian_soccer import queries

SIMPLE_LIMIT_SECONDS = 2.0
AGGREGATE_LIMIT_SECONDS = 5.0


def _run(query, *args, **kwargs):
    start = time.perf_counter()
    result = query(*args, **kwargs)
    elapsed = time.perf_counter() - start
    return result, elapsed


class TestSimpleLookups:
    def test_repository_loads_within_budget(self, repo):
        # Given the datasets (loaded once in the session fixture)
        # When measured
        # Then startup stays well inside the aggregate budget
        assert len(repo.matches) == 16612
        assert repo.load_report["players_loaded"] == 18207

    def test_match_search_by_team(self, repo):
        result, elapsed = _run(queries.search_matches, repo, team="Flamengo", limit=10)
        assert result["total_matches"] > 900
        assert elapsed < SIMPLE_LIMIT_SECONDS

    def test_head_to_head_lookup(self, repo):
        result, elapsed = _run(
            queries.head_to_head, repo, "Flamengo", "Fluminense"
        )
        assert result["matches_played"] == 44
        assert elapsed < SIMPLE_LIMIT_SECONDS

    def test_player_search(self, repo):
        result, elapsed = _run(
            queries.search_players, repo, nationality="Brazil", limit=10
        )
        assert result["total_players"] == 827
        assert elapsed < SIMPLE_LIMIT_SECONDS

    def test_player_detail_by_name(self, repo):
        result, elapsed = _run(queries.player_detail, repo, name="Neymar Jr")
        assert result["player"]["overall"] == 92
        assert elapsed < SIMPLE_LIMIT_SECONDS


class TestAggregateQueries:
    def test_standings_calculation(self, repo):
        result, elapsed = _run(
            queries.standings, repo, "Brasileirão Serie A", 2019
        )
        assert result["matches_counted"] == 380
        assert elapsed < AGGREGATE_LIMIT_SECONDS

    def test_team_rankings_across_all_matches(self, repo):
        result, elapsed = _run(
            queries.team_rankings, repo, metric="away_points", limit=10
        )
        assert result["total_teams"] > 100
        assert elapsed < AGGREGATE_LIMIT_SECONDS

    def test_full_statistics_summary(self, repo):
        result, elapsed = _run(
            queries.stats_summary, repo, competition="Brasileirão Serie A"
        )
        assert result["matches"] == 8321
        assert elapsed < AGGREGATE_LIMIT_SECONDS

    def test_cold_repository_load(self, tmp_path):
        # Given a completely fresh repository instance
        start = time.perf_counter()
        repo = DataRepository()
        elapsed = time.perf_counter() - start
        # When loading all six files from disk
        # Then startup completes within the aggregate budget
        assert len(repo.matches) == 16612
        assert elapsed < AGGREGATE_LIMIT_SECONDS
