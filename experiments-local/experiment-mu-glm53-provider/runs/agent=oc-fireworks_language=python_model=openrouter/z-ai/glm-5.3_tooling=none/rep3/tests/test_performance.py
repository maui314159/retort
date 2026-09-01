"""Feature: Query Performance (spec success criteria)

    Scenario: Simple lookups respond in under 2 seconds
      Given the in-memory dataset
      When I run simple lookup queries
      Then each completes in under 2 seconds

    Scenario: Aggregate queries respond in under 5 seconds
      When I run aggregate queries (standings, stats, best records)
      Then each completes in under 5 seconds
"""

from __future__ import annotations

import time

import pytest

from brsoccer import queries as q

pytestmark = pytest.mark.performance


def _timed(fn, *args, **kwargs):
    start = time.monotonic()
    result = fn(*args, **kwargs)
    return result, time.monotonic() - start


class TestSimpleLookupLatency:
    """Scenario: Simple lookups respond in < 2 seconds."""

    def test_last_match_lookup(self, sd):
        # When I look up Flamengo's last match
        _, elapsed = _timed(q.last_match, sd, "Flamengo", "Corinthians")
        # Then it answers in well under 2 seconds
        assert elapsed < 2.0

    def test_team_match_search(self, sd):
        # When I search a team's matches
        matches, elapsed = _timed(q.find_matches, sd, team="Palmeiras", season=2023)
        # Then results arrive in under 2 seconds
        assert matches and elapsed < 2.0

    def test_player_name_search(self, sd):
        # When I search players by name
        players, elapsed = _timed(q.search_players, sd, name="Neymar")
        # Then the answer is immediate
        assert players and elapsed < 2.0


class TestAggregateQueryLatency:
    """Scenario: Aggregate queries respond in < 5 seconds."""

    def test_standings_computation(self, sd):
        # When I compute a full season table
        table, elapsed = _timed(q.standings, sd, "serie_a", 2019)
        # Then it completes in under 5 seconds
        assert table and elapsed < 5.0

    def test_dataset_wide_stats(self, sd):
        # When I aggregate the entire dataset
        stats, elapsed = _timed(q.competition_stats, sd)
        # Then it completes in under 5 seconds
        assert stats["matches"] > 15000 and elapsed < 5.0

    def test_best_records_ranking(self, sd):
        # When I rank every team's home record
        ranked, elapsed = _timed(q.best_records, sd, venue="home", min_matches=50)
        # Then it completes in under 5 seconds
        assert ranked and elapsed < 5.0

    def test_head_to_head_across_all_matches(self, sd):
        # When I compute a head-to-head over all competitions
        h2h, elapsed = _timed(q.head_to_head, sd, "Flamengo", "Fluminense")
        # Then it completes in under 5 seconds
        assert h2h["matches"] and elapsed < 5.0


class TestMcpToolLatency:
    """Scenario: MCP tool round-trips stay fast (in-process server)."""

    @pytest.mark.parametrize(
        ("tool", "args"),
        [
            ("last_match", {"team": "Flamengo"}),
            ("search_players", {"nationality": "Brazil", "min_overall": 85}),
            ("standings", {"competition": "serie_a", "season": 2019}),
            ("data_summary", {}),
        ],
    )
    def test_tool_round_trip(self, server, tool, args):
        from conftest import call_tool

        start = time.monotonic()
        answer = call_tool(server, tool, args)
        elapsed = time.monotonic() - start
        # Then every round trip answers within the simple-query budget
        assert answer
        assert elapsed < 2.0, f"{tool} took {elapsed:.2f}s"
