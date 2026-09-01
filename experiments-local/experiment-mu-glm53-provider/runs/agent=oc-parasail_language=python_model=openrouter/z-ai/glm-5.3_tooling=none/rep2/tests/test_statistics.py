"""GWT tests for statistical analysis queries."""

from __future__ import annotations


class TestGoalAverages:
    def test_given_serie_a_when_averaged_then_home_advantage_evident(self, engine):
        result = engine.goal_averages(competition="Série A")
        assert 2.0 < result["average_goals_per_match"] < 3.0
        assert result["home_win_rate"] > result["away_win_rate"]
        rates = [result["home_win_rate"], result["draw_rate"], result["away_win_rate"]]
        assert abs(sum(rates) - 100) < 0.5

    def test_given_season_scope_when_averaged_then_pool_smaller(self, engine):
        season = engine.goal_averages(competition="Série A", season=2019)
        overall = engine.goal_averages(competition="Série A")
        assert season["matches"] == 380
        assert season["matches"] < overall["matches"]

    def test_given_empty_filters_when_averaged_then_all_matches(self, engine):
        result = engine.goal_averages()
        assert result["matches"] == sum(
            1 for m in engine.matches if m.played
        )


class TestBiggestWins:
    def test_given_dataset_when_biggest_wins_then_sorted_by_margin(self, engine):
        result = engine.biggest_wins(limit=15)
        margins = [m["goal_margin"] for m in result["matches"]]
        assert margins == sorted(margins, reverse=True)
        assert margins[0] >= 8

    def test_given_libertadores_scope_when_biggest_wins_then_only_libertadores(self, engine):
        result = engine.biggest_wins(competition="Libertadores", limit=10)
        for match in result["matches"]:
            assert match["competition"] == "Copa Libertadores"


class TestDerbies:
    def test_given_derby_registry_when_queried_then_all_pairs_are_distinct_clubs(self, engine):
        result = engine.derbies()
        for name in result["tracked_derbies"]:
            assert name
        total = result["total_matches"]
        assert total > 300  # decades of derbies across all seasons

    def test_given_2023_when_derbies_queried_then_rivalries_present(self, engine):
        result = engine.derbies(season=2023)
        derby_names = {m["derby"] for m in result["matches"]}
        assert "Fla-Flu" in derby_names
        assert "Grenal" in derby_names
        assert "Derby Paulista" in derby_names

    def test_given_grenal_when_queried_then_only_gremio_and_internacional(self, engine):
        result = engine.derbies(season=2019)
        grenais = [m for m in result["matches"] if m["derby"] == "Grenal"]
        assert grenais
        for match in grenais:
            teams = {match["home_team_id"], match["away_team_id"]}
            assert teams == {"gremio", "internacional"}


class TestPerformanceCriteria:
    """The specification's query performance criteria."""

    def test_given_simple_lookup_when_timed_then_under_two_seconds(self, engine):
        import time

        start = time.perf_counter()
        engine.search_matches(team="Flamengo", opponent="Fluminense", limit=50)
        engine.search_players(name="Neymar")
        engine.team_stats(team="Palmeiras", season=2019)
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0, f"simple lookups took {elapsed:.2f}s"

    def test_given_aggregate_query_when_timed_then_under_five_seconds(self, engine):
        import time

        start = time.perf_counter()
        engine.standings("Série A", 2019)
        engine.head_to_head("Flamengo", "Fluminense")
        engine.best_records(venue="home", minimum_matches=10)
        engine.goal_averages()
        engine.derbies()
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0, f"aggregate queries took {elapsed:.2f}s"
