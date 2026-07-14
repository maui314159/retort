"""
Context
=======
Module: tests.test_match_queries
Purpose: BDD (Given-When-Then) scenarios for the Match Queries capability —
         finding matches by team/opponent/competition/season/date and computing
         head-to-head records. Exercises the real bundled data via the shared
         ``kb`` fixture.
"""

from __future__ import annotations


class TestFindMatchesBetweenTwoTeams:
    """Feature: Find matches between two teams."""

    def test_returns_matches_with_required_fields(self, kb):
        # Given the match data is loaded
        # When I search for matches between Flamengo and Fluminense
        matches = kb.find_matches(team="Flamengo", opponent="Fluminense")
        # Then I should receive a non-empty list
        assert matches, "expected Fla-Flu fixtures in dataset"
        # And each match has date, scores, and competition
        for m in matches:
            assert m["date"] is not None
            assert isinstance(m["home_goal"], int)
            assert isinstance(m["away_goal"], int)
            assert m["competition"]
        # And every returned match actually involves both teams
        for m in matches:
            names = (m["home_team"] + m["away_team"]).lower()
            assert "flamengo" in names and "fluminense" in names

    def test_results_sorted_newest_first(self, kb):
        matches = kb.find_matches(team="Palmeiras", limit=20)
        dates = [m["date"] for m in matches if m["date"]]
        assert dates == sorted(dates, reverse=True)


class TestFindMatchesBySeasonAndCompetition:
    """Feature: Filter matches by season and competition."""

    def test_season_filter(self, kb):
        # When I ask what matches Palmeiras played in 2019
        matches = kb.find_matches(team="Palmeiras", season=2019, limit=100)
        # Then every result is from 2019
        assert matches
        assert all(m["season"] == 2019 for m in matches)

    def test_competition_filter(self, kb):
        matches = kb.find_matches(team="Flamengo", competition="Libertadores", limit=100)
        assert matches
        assert all(m["competition"] == "Copa Libertadores" for m in matches)

    def test_partial_team_name_without_suffix(self, kb):
        # Given names in data carry state suffixes ("Corinthians-SP")
        # When I query the bare name
        matches = kb.find_matches(team="Corinthians", season=2019, limit=100)
        # Then it still resolves
        assert matches


class TestHeadToHead:
    """Feature: Head-to-head record between two teams."""

    def test_record_totals_are_consistent(self, kb):
        # When I request the Flamengo vs Fluminense head-to-head
        h2h = kb.head_to_head("Flamengo", "Fluminense")
        # Then wins + draws account for every match
        assert h2h["matches"] > 0
        assert h2h["team_a_wins"] + h2h["team_b_wins"] + h2h["draws"] == h2h["matches"]
        # And the fixture sample never exceeds the total
        assert len(h2h["fixtures"]) <= h2h["matches"]

    def test_orientation_independent(self, kb):
        # The record is symmetric: swapping args swaps the win columns.
        ab = kb.head_to_head("Santos", "Palmeiras")
        ba = kb.head_to_head("Palmeiras", "Santos")
        assert ab["matches"] == ba["matches"]
        assert ab["team_a_wins"] == ba["team_b_wins"]
        assert ab["draws"] == ba["draws"]
