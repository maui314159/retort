"""
Context
=======
Module: tests.test_team_and_competition
Purpose: BDD (Given-When-Then) scenarios for Team Queries and Competition
         Queries — win/draw/loss records, venue splits, league standings and
         the per-team competition list. Standings assertions are anchored to the
         historically known 2019 Brasileirão so a regression in dedup or
         team-identity keys is caught immediately.
"""

from __future__ import annotations


class TestTeamStatistics:
    """Feature: Get team statistics."""

    def test_record_components_sum_to_matches(self, kb):
        # When I request Palmeiras' 2019 Série A record
        s = kb.team_stats("Palmeiras", season=2019, competition="Brasileirão Série A")
        # Then W+D+L equals matches played
        assert s["matches"] > 0
        assert s["wins"] + s["draws"] + s["losses"] == s["matches"]
        # And points follow the 3-1-0 rule
        assert s["points"] == s["wins"] * 3 + s["draws"]

    def test_home_record_subset_of_total(self, kb):
        # Given a full-season record and a home-only record
        total = kb.team_stats("Corinthians", season=2019, competition="Brasileirão Série A")
        home = kb.team_stats("Corinthians", season=2019, competition="Brasileirão Série A", venue="home")
        # Then home matches are a subset of all matches
        assert 0 < home["matches"] <= total["matches"]

    def test_win_rate_is_percentage(self, kb):
        s = kb.team_stats("Flamengo", season=2019, competition="Brasileirão Série A")
        assert 0.0 <= s["win_rate"] <= 100.0


class TestStandings:
    """Feature: Compute league standings from match results."""

    def test_2019_serie_a_has_twenty_teams_each_38_games(self, kb):
        # Given the historical 20-team double round-robin
        table = kb.standings("Brasileirão Série A", 2019)
        assert len(table) == 20
        assert all(row["played"] == 38 for row in table)

    def test_2019_champion_is_flamengo_with_90_points(self, kb):
        # Then the known champion tops the table with the known points total
        table = kb.standings("Brasileirão Série A", 2019)
        champion = table[0]
        assert "Flamengo" in champion["team"]
        assert champion["points"] == 90
        assert (champion["wins"], champion["draws"], champion["losses"]) == (28, 6, 4)

    def test_table_sorted_by_points_then_gd(self, kb):
        table = kb.standings("Brasileirão Série A", 2019)
        keys = [(-r["points"], -r["goal_difference"], -r["goals_for"]) for r in table]
        assert keys == sorted(keys)

    def test_same_base_clubs_not_merged(self, kb):
        # Invariant: Atlético-MG and Atlético-PR are distinct rows, never merged
        # into one inflated entry.
        table = kb.standings("Brasileirão Série A", 2019)
        assert max(r["played"] for r in table) == 38


class TestTeamCompetitions:
    """Feature: List competitions a team has played in."""

    def test_palmeiras_spans_multiple_competitions(self, kb):
        comps = kb.competitions_for_team("Palmeiras")
        names = {c["competition"] for c in comps}
        assert "Brasileirão Série A" in names
        # Palmeiras appears in continental and cup data too.
        assert len(names) >= 2
        assert all(c["matches"] > 0 for c in comps)
