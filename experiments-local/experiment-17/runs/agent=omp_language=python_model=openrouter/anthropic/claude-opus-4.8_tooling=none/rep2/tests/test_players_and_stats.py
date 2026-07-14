"""
Context
=======
Module: tests.test_players_and_stats
Purpose: BDD (Given-When-Then) scenarios for Player Queries and Statistical
         Analysis — FIFA player search by name/nationality/position/rating, the
         Brazilian-players-by-club summary, aggregate goal statistics, and
         biggest-margin matches.
"""

from __future__ import annotations


class TestPlayerSearch:
    """Feature: Search the FIFA player database."""

    def test_search_by_name(self, kb):
        # When I search for "Neymar"
        players = kb.find_players(name="Neymar")
        # Then I get at least one matching player with rating fields
        assert players
        assert any("Neymar" in (p["name"] or "") for p in players)
        assert all(isinstance(p["overall"], int) for p in players)

    def test_brazilian_players_sorted_by_overall_desc(self, kb):
        # When I list Brazilian players
        players = kb.find_players(nationality="Brazil", limit=50)
        assert players
        # Then all are Brazilian
        assert all(p["nationality"] == "Brazil" for p in players)
        # And sorted by Overall descending
        overalls = [p["overall"] for p in players]
        assert overalls == sorted(overalls, reverse=True)
        # And the top Brazilian is Neymar (known top of FIFA dataset)
        assert "Neymar" in players[0]["name"]

    def test_filter_by_position_and_min_rating(self, kb):
        players = kb.find_players(position="GK", min_overall=85, limit=50)
        assert players
        assert all(p["position"] == "GK" for p in players)
        assert all(p["overall"] >= 85 for p in players)

    def test_filter_by_club(self, kb):
        # Santos fields players in the FIFA dataset.
        players = kb.find_players(club="Santos", limit=50)
        assert players
        assert all("santos" in (p["club"] or "").lower() for p in players)


class TestPlayersByClubSummary:
    """Feature: Brazilian players grouped by club."""

    def test_summary_rows_have_counts_and_avg(self, kb):
        rows = kb.players_by_club_summary("Brazil", top=10)
        assert rows
        assert all(r["players"] > 0 for r in rows)
        assert all(0 <= r["avg_overall"] <= 99 for r in rows)
        # Sorted by player count descending.
        counts = [r["players"] for r in rows]
        assert counts == sorted(counts, reverse=True)


class TestStatisticalAnalysis:
    """Feature: Aggregate statistics."""

    def test_average_goals_per_match_is_plausible(self, kb):
        # When I compute Série A aggregate stats
        s = kb.competition_stats(competition="Brasileirão Série A")
        # Then the average goals per match is in a sane football range
        assert s["matches"] > 1000
        assert 2.0 <= s["avg_goals_per_match"] <= 3.5
        # And outcome rates sum to ~100%
        assert abs(s["home_win_rate"] + s["away_win_rate"] + s["draw_rate"] - 100.0) < 0.5
        # And home advantage holds in the aggregate
        assert s["home_win_rate"] > s["away_win_rate"]

    def test_biggest_wins_ordered_by_margin(self, kb):
        rows = kb.biggest_wins(competition="Brasileirão Série A", limit=10)
        assert rows
        margins = [r["margin"] for r in rows]
        assert margins == sorted(margins, reverse=True)
        assert margins[0] >= 5  # there exist big blowouts

    def test_top_scoring_team_2019_is_flamengo(self, kb):
        # The 2019 champion was also the top-scoring side.
        rows = kb.top_scoring_teams(competition="Brasileirão Série A", season=2019, limit=5)
        assert rows
        assert "Flamengo" in rows[0]["team"]
        # Goals descending.
        goals = [r["goals"] for r in rows]
        assert goals == sorted(goals, reverse=True)
