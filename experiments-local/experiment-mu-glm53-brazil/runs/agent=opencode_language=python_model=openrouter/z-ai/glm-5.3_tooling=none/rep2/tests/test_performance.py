"""Performance tests mirroring the spec's query-performance criteria.

The specification requires simple lookups to answer in under 2 seconds and
aggregate queries in under 5 seconds; data loading happens once at service
construction (a session fixture), mirroring the MCP server's startup.
"""

from __future__ import annotations

import time

SIMPLE_LOOKUP_BUDGET = 2.0
AGGREGATE_BUDGET = 5.0


def _timed(call):
    start = time.perf_counter()
    result = call()
    return time.perf_counter() - start, result


def test_simple_lookup_matches_under_two_seconds(service):
    elapsed, result = _timed(
        lambda: service.search_matches(team="Flamengo", opponent="Fluminense")
    )
    assert elapsed < SIMPLE_LOOKUP_BUDGET
    assert result["total"] > 0


def test_simple_lookup_players_under_two_seconds(service):
    elapsed, result = _timed(
        lambda: service.search_players(nationality="Brazil", limit=10)
    )
    assert elapsed < SIMPLE_LOOKUP_BUDGET
    assert result["total"] > 0


def test_aggregate_standings_under_five_seconds(service):
    elapsed, result = _timed(
        lambda: service.standings("Brasileirão Série A", 2019)
    )
    assert elapsed < AGGREGATE_BUDGET
    assert result["champion"]


def test_aggregate_best_records_under_five_seconds(service):
    elapsed, result = _timed(lambda: service.best_records(venue="home"))
    assert elapsed < AGGREGATE_BUDGET
    assert result["records"]


def test_aggregate_league_statistics_under_five_seconds(service):
    elapsed, result = _timed(lambda: service.league_statistics())
    assert elapsed < AGGREGATE_BUDGET
    assert result["matches"] > 10000
