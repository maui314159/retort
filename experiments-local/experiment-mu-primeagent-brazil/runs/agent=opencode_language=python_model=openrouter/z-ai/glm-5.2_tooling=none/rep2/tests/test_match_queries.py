"""BDD tests: match queries.

Feature: Match Queries
  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition

  Scenario: Filter by competition and season
    Given the match data is loaded
    When I search for Brasileirao matches in season 2019
    Then every returned match is from the Brasileirao and season 2019
"""
from __future__ import annotations

from brsl.query_engine import QueryEngine


class TestMatchQueries:
    # Scenario: matches between two teams
    def test_matches_between_two_teams(self, engine: QueryEngine):
        # When I search for matches between Flamengo and Fluminense
        result = engine.search_matches(team="Flamengo", opponent="Fluminense")
        # Then I should receive a non-empty list of matches
        assert result["count"] > 0
        for m in result["matches"]:
            # And each match should have date, scores, and competition
            assert "date" in m
            assert "home_goal" in m
            assert "away_goal" in m
            assert "competition" in m
            teams = {m["home_team"], m["away_team"]}
            assert any("Flamengo" in t or "flamengo" in t.lower()
                       for t in teams)

    # Scenario: filter by competition and season
    def test_filter_by_competition_and_season(self, engine: QueryEngine):
        result = engine.search_matches(competition="brasileirao", season=2019)
        assert result["count"] > 0
        # every returned match must be a 2019 Brasileirao match
        assert all(m["season"] == 2019 for m in result["matches"])
        assert all(m["source"] == "brasileirao" for m in result["matches"])

    # Scenario: filter by team
    def test_filter_by_team(self, engine: QueryEngine):
        result = engine.search_matches(team="Palmeiras", season=2019)
        assert result["count"] > 0
        for m in result["matches"]:
            teams = {m["home_team"], m["away_team"]}
            assert any("Palmeiras" in t for t in teams)

    # Scenario: date range filter
    def test_date_range_filter(self, engine: QueryEngine):
        result = engine.search_matches(
            competition="libertadores",
            date_from="2019-01-01", date_to="2019-12-31")
        for m in result["matches"]:
            assert m["date"] is None or m["date"].startswith("2019")

    # Scenario: limit is honoured
    def test_limit_is_honoured(self, engine: QueryEngine):
        result = engine.search_matches(competition="brasileirao", limit=5)
        assert result["showing"] == 5
        assert result["count"] >= 5

    # Scenario: Copa do Brasil finals (knockout rounds)
    def test_copa_do_brasil_searchable(self, engine: QueryEngine):
        result = engine.search_matches(competition="copa do brasil", limit=10)
        assert result["count"] > 0
