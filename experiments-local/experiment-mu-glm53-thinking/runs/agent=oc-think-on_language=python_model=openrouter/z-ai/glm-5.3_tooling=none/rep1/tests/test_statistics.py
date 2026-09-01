"""Feature: Statistical Analysis

BDD scenarios for the TASK.md examples:
- "What's the average goals per match in the Brasileirão?"
- "Which team has the best away/home record?"
- "Show me the biggest wins in the dataset"
- Derbies, extended match statistics, and query performance.
"""

from __future__ import annotations

import time

from brazilian_soccer import queries as q
from brazilian_soccer.normalize import TeamResolutionError


class TestCompetitionStatistics:
    """Feature: Statistical Analysis - aggregate competition statistics."""

    def test_average_goals_per_match_in_the_brasileirao(self, soccer):
        """Scenario: 'What's the average goals per match in the Brasileirão?'"""
        # Given all played Série A matches 2003-2023
        # When I request competition statistics
        result = q.competition_stats(soccer, "Brasileirão Série A")
        # Then goals, averages and home/away splits are returned
        assert result["matches"] == 8321
        assert result["avg_goals_per_match"] == 2.57
        assert result["home_win_rate"] == 49.7
        assert result["home_win_rate"] + result["draw_rate"] + result["away_win_rate"] == 100.0
        assert result["biggest_win"]["score"] is not None
        assert result["date_range"]["from"].startswith("2003")

    def test_season_scoped_statistics(self, soccer):
        # Given the 2019 Série A season
        # When I request its statistics
        result = q.competition_stats(soccer, "Série A", 2019)
        # Then they are computed over the full 380 matches
        assert result["matches"] == 380
        assert 2.0 < result["avg_goals_per_match"] < 3.0
        assert result["season"] == 2019

    def test_stats_for_a_season_without_matches_are_rejected(self, soccer):
        try:
            q.competition_stats(soccer, "Libertadores", 2012)
            raised = False
        except TeamResolutionError as exc:
            raised = True
            assert "No matches found" in str(exc)
        assert raised


class TestBiggestWins:
    """Feature: Statistical Analysis - Scenario: biggest wins in the dataset."""

    def test_biggest_libertadores_wins(self, soccer):
        # Given all Libertadores matches
        # When I ask for the biggest wins
        result = q.biggest_wins(soccer, competition="Libertadores", limit=3)
        # Then 8-0 scorelines lead the list with winner and margin
        first = result["matches"][0]
        assert first["margin"] == 8
        assert first["winner"] == "River Plate"
        assert (first["home"], first["away"], first["score"]) == (
            "River Plate", "Jorge Wilstermann", "8-0",
        )
        margins = [m["margin"] for m in result["matches"]]
        assert margins == sorted(margins, reverse=True)

    def test_biggest_wins_for_a_season(self, soccer):
        # Given the 2019 Série A
        # When I ask for its biggest win
        result = q.biggest_wins(soccer, competition="Série A", season=2019, limit=1)
        # Then the top margin is returned with the winner
        assert result["matches"][0]["season"] == 2019
        assert result["matches"][0]["margin"] >= 4
        assert result["matches"][0]["winner"] in (
            result["matches"][0]["home"],
            result["matches"][0]["away"],
        )


class TestBestRecords:
    """Feature: Statistical Analysis - Scenario: 'Which team has the best home record?'."""

    def test_best_home_records_2019(self, soccer):
        # Given the 2019 Série A
        # When I rank home records
        result = q.best_home_records(soccer, "Série A", 2019, limit=3)
        # Then Flamengo's famous 2019 home form leads
        top = result["best_home_records"][0]
        assert top["team"] == "Flamengo"
        assert top["home_matches"] == 19
        assert top["home_wins"] == 17
        assert top["home_win_rate"] == 89.5

    def test_best_away_team_via_team_stats(self, soccer):
        # Given the 2019 Série A
        # When Flamengo's away record is checked
        result = q.team_stats(soccer, "Flamengo", season=2019, competition="Série A", venue="away")
        # Then the champions had the league's best away record
        assert result["record"]["wins"] == 11
        assert result["record"]["matches"] == 19


class TestDerbyMatches:
    """Feature: Statistical Analysis - Scenario: 'Show me all derbies'."""

    def test_named_derby_with_record(self, soccer):
        # Given the Gre-Nal rivalry
        # When I ask for its 2019 matches
        result = q.derby_matches(soccer, "Gre-Nal", season=2019)
        # Then both meetings of the season are returned
        derby = result["derbies"][0]
        assert derby["teams"] == ["Grêmio", "Internacional"]
        assert derby["total_matches"] == 2
        assert len(derby["matches"]) == 2

    def test_all_derbies_in_a_season(self, soccer):
        # Given the 2023 season
        # When I sweep every rivalry
        result = q.derby_matches(soccer, season=2023)
        # Then multiple classic derbies are found
        played = {d["derby"]: d["total_matches"] for d in result["derbies"]}
        assert played["Fla-Flu"] == 4
        assert played["Gre-Nal"] == 2
        assert sum(played.values()) > 20

    def test_unknown_derby_is_rejected(self, soccer):
        # Given an unknown rivalry name
        # When I query derbies
        # Then a helpful error lists the known derbies
        try:
            q.derby_matches(soccer, derby="El Clásico")
            raised = False
        except TeamResolutionError as exc:
            raised = True
            assert "Known derbies" in str(exc)
        assert raised


class TestExtendedMatchStats:
    """Feature: Statistical Analysis - corners, shots and attacks."""

    def test_match_stats_with_corners_shots_attacks(self, soccer):
        # Given the BR-Football extended dataset
        # When I ask for Palmeiras' 2023 Série A match statistics
        result = q.search_match_stats(
            soccer, team="Palmeiras", season=2023, competition="Série A", limit=5
        )
        # Then every match carries corners, shots and attacks
        # (BR-Football lists 37 of Palmeiras' 38 league fixtures for 2023)
        assert result["total_matches"] == 37
        for match in result["matches"]:
            stats = match["stats"]
            assert set(stats) == {"corners", "shots", "attacks", "half_time"}
            assert stats["corners"]["home"] is not None
            assert stats["shots"]["away"] is not None

    def test_match_stats_head_to_head(self, soccer):
        # Given the extended dataset
        # When I ask for matches between two teams
        result = q.search_match_stats(soccer, team="Flamengo", opponent="São Paulo", limit=10)
        # Then only fixtures between the two are returned
        assert result["total_matches"] > 0
        for match in result["matches"]:
            assert {match["home"], match["away"]} == {"Flamengo", "São Paulo"}


class TestQueryPerformance:
    """Feature: Query Performance (TASK.md: lookups < 2s, aggregates < 5s)."""

    def test_simple_lookup_under_two_seconds(self, soccer):
        # Given a simple lookup query
        start = time.perf_counter()
        q.search_matches(soccer, team="Flamengo", opponent="Fluminense")
        # When it is executed in memory
        elapsed = time.perf_counter() - start
        # Then it responds in under 2 seconds
        assert elapsed < 2.0

    def test_aggregate_query_under_five_seconds(self, soccer):
        # Given an aggregate query across all matches
        start = time.perf_counter()
        q.competition_stats(soccer, "Brasileirão Série A")
        q.standings(soccer, "Série A", 2019)
        q.biggest_wins(soccer)
        # When executed
        elapsed = time.perf_counter() - start
        # Then it responds in under 5 seconds with no timeout
        assert elapsed < 5.0

    def test_player_search_under_two_seconds(self, soccer):
        start = time.perf_counter()
        q.search_players(soccer, nationality="Brazil", min_overall=80)
        assert time.perf_counter() - start < 2.0
