"""
Performance tests for the TASK.md "Query Performance" success criteria:

    Simple lookups respond in < 2 seconds
    Aggregate queries respond in < 5 seconds
    No timeout errors

The dataset is loaded once (session fixture) as it would be in the running
server; every tool call afterwards is a pure in-memory operation.
"""

from __future__ import annotations

import time

from soccer_mcp import tools
from soccer_mcp.data_loader import load_dataset

SIMPLE_LIMIT_SECONDS = 2.0
AGGREGATE_LIMIT_SECONDS = 5.0


def _timed(fn, *args, **kwargs):
    start = time.perf_counter()
    result = fn(*args, **kwargs)
    return time.perf_counter() - start, result


def test_simple_lookup_under_2s():
    """When did Flamengo last play Corinthians? (spec simple lookup)"""
    elapsed, answer = _timed(
        tools.last_match, team="Flamengo", opponent="Corinthians")
    assert elapsed < SIMPLE_LIMIT_SECONDS, f"took {elapsed:.2f}s"
    assert "Flamengo" in answer


def test_player_lookup_under_2s():
    elapsed, answer = _timed(tools.find_player, name="Neymar")
    assert elapsed < SIMPLE_LIMIT_SECONDS, f"took {elapsed:.2f}s"
    assert "Neymar" in answer


def test_team_resolution_under_2s():
    elapsed, answer = _timed(tools.find_team, name="Sport Club Corinthians Paulista")
    assert elapsed < SIMPLE_LIMIT_SECONDS, f"took {elapsed:.2f}s"
    assert "corinthians sp" in answer


def test_head_to_head_under_5s():
    elapsed, answer = _timed(
        tools.head_to_head, team_a="Palmeiras", team_b="Santos")
    assert elapsed < AGGREGATE_LIMIT_SECONDS, f"took {elapsed:.2f}s"
    assert "Head-to-head" in answer


def test_standings_under_5s():
    elapsed, answer = _timed(
        tools.standings, competition="Brasileirão", season=2019)
    assert elapsed < AGGREGATE_LIMIT_SECONDS, f"took {elapsed:.2f}s"
    assert "Champion" in answer


def test_aggregate_statistics_under_5s():
    elapsed, answer = _timed(
        tools.competition_stats, competition="Brasileirão")
    assert elapsed < AGGREGATE_LIMIT_SECONDS, f"took {elapsed:.2f}s"
    assert "Average goals per match" in answer


def test_biggest_wins_under_5s():
    elapsed, answer = _timed(tools.biggest_wins, limit=10)
    assert elapsed < AGGREGATE_LIMIT_SECONDS, f"took {elapsed:.2f}s"
    assert "Biggest victories" in answer


def test_full_dataset_load_under_15s():
    """One-time startup cost: all six CSVs load comfortably fast."""
    start = time.perf_counter()
    dataset = load_dataset()
    elapsed = time.perf_counter() - start
    assert elapsed < 15.0, f"dataset load took {elapsed:.2f}s"
    assert len(dataset.matches) > 20000
