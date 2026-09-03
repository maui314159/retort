"""
Context block
=============
Brazilian Soccer MCP Server - Performance Tests
------------------------------------------------
Spec requires: simple lookups < 2s, aggregate queries < 5s, no timeouts.
"""

from __future__ import annotations

import time

import pytest

from brazilian_soccer_mcp import get_engine


@pytest.fixture(scope="module")
def engine():
    return get_engine()


def test_simple_lookup_under_2_seconds(engine):
    start = time.perf_counter()
    res = engine.find_matches(team="Flamengo", opponent="Fluminense", limit=50)
    elapsed = time.perf_counter() - start
    assert isinstance(res, list)
    assert elapsed < 2.0, f"simple lookup took {elapsed:.2f}s"


def test_player_lookup_under_2_seconds(engine):
    start = time.perf_counter()
    res = engine.search_players(nationality="Brazil", limit=50)
    elapsed = time.perf_counter() - start
    assert len(res) > 0
    assert elapsed < 2.0, f"player lookup took {elapsed:.2f}s"


def test_aggregate_query_under_5_seconds(engine):
    start = time.perf_counter()
    res = engine.standings(competition="brasileirao", season=2019)
    elapsed = time.perf_counter() - start
    assert len(res) == 20
    assert elapsed < 5.0, f"aggregate query took {elapsed:.2f}s"


def test_biggest_wins_under_5_seconds(engine):
    start = time.perf_counter()
    res = engine.biggest_wins(limit=50)
    elapsed = time.perf_counter() - start
    assert len(res) > 0
    assert elapsed < 5.0, f"biggest wins took {elapsed:.2f}s"
