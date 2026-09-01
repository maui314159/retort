"""BDD tests for the analysis/query engine (analysis.py).

Context block
-------------
Feature: Match Queries, Team Queries, Competition Queries, Statistical
Analysis, and Player Queries — covering the five required capability
categories from TASK.md.

Scenarios follow Given/When/Then structure per the spec's BDD mandate.
"""
from __future__ import annotations

from analysis import (
    avg_goals, best_home_record, biggest_wins, champion, derbies,
    head_to_head, players_at_club, relegated, search_matches,
    search_players, standings, team_stats, top_brazilian_players,
)
from data_loader import SoccerData


# ---------------------------------------------------------------------------
# Feature: Match Queries
# ---------------------------------------------------------------------------

class TestMatchQueries:
    # Scenario: Find matches between two teams
    def test_flamengo_vs_fluminense(self, sd: SoccerData):
        # Given the match data is loaded
        # When I search for matches between Flamengo and Fluminense
        results = search_matches(sd, team="Flamengo", opponent="Fluminense", limit=200)
        # Then I should receive a list of matches
        assert len(results) > 0
        # And each match should have date, scores, and competition
        for m in results:
            assert "date" in m and "score" in m and "competition" in m
            assert "Flamengo" in (m["home_team"], m["away_team"])
            assert "Fluminense" in (m["home_team"], m["away_team"])

    # Scenario: Filter by season
    def test_palmeiras_2022(self, sd: SoccerData):
        results = search_matches(sd, team="Palmeiras", season=2022, limit=200)
        assert len(results) > 0
        assert all(m["season"] == 2022 for m in results)

    # Scenario: Filter by competition
    def test_libertadores_only(self, sd: SoccerData):
        results = search_matches(sd, competition="Libertadores", limit=50)
        assert len(results) > 0
        assert all(m["competition"] == "Libertadores" for m in results)

    # Scenario: Date range filter
    def test_date_range(self, sd: SoccerData):
        results = search_matches(sd, team="Flamengo",
                                 start_date="2020-01-01", end_date="2020-12-31", limit=200)
        assert all(m["date"] is None or "2020-" in m["date"] for m in results)

    # Scenario: Limit is respected
    def test_limit(self, sd: SoccerData):
        results = search_matches(sd, team="Flamengo", limit=5)
        assert len(results) <= 5


# ---------------------------------------------------------------------------
# Feature: Team Queries
# ---------------------------------------------------------------------------

class TestTeamQueries:
    # Scenario: Get team statistics for a season
    def test_palmeiras_2023_stats(self, sd: SoccerData):
        # Given the match data is loaded
        # When I request statistics for Palmeiras in season 2022
        stats = team_stats(sd, "Palmeiras", season=2022)
        # Then I should receive wins, losses, draws, and goals
        assert stats["played"] > 0
        assert stats["wins"] + stats["draws"] + stats["losses"] == stats["played"]
        assert stats["goals_for"] >= 0
        assert stats["goals_against"] >= 0
        assert 0.0 <= stats["win_rate"] <= 1.0

    # Scenario: Home/away split is consistent
    def test_home_away_split(self, sd: SoccerData):
        stats = team_stats(sd, "Flamengo", season=2022)
        h = stats["home"]
        a = stats["away"]
        assert h["wins"] + h["draws"] + h["losses"] + a["wins"] + a["draws"] + a["losses"] == stats["played"]

    # Scenario: Head-to-head record
    def test_head_to_head(self, sd: SoccerData):
        h2h = head_to_head(sd, "Flamengo", "Fluminense")
        assert h2h["team_a"] == "Flamengo"
        assert h2h["team_b"] == "Fluminense"
        assert h2h["team_a_wins"] + h2h["team_b_wins"] + h2h["draws"] == len(h2h["matches"])
        assert len(h2h["matches"]) > 0

    # Scenario: Head-to-head is symmetric
    def test_head_to_head_symmetric(self, sd: SoccerData):
        a = head_to_head(sd, "Corinthians", "São Paulo")
        b = head_to_head(sd, "São Paulo", "Corinthians")
        assert a["team_a_wins"] == b["team_b_wins"]
        assert a["team_b_wins"] == b["team_a_wins"]


# ---------------------------------------------------------------------------
# Feature: Competition Queries
# ---------------------------------------------------------------------------

class TestCompetitionQueries:
    # Scenario: Standings for a Brasileirão season
    def test_standings_2019_brasileirao(self, sd: SoccerData):
        # Given matches exist for 2019
        # When I compute standings for Brasileirão 2019
        table = standings(sd, "Brasileirão", 2019)
        # Then a table is returned, sorted by points desc
        assert len(table) >= 10
        assert table[0]["points"] >= table[1]["points"]
        assert table[0]["position"] == 1
        # 2019 Brasileirão champion was Flamengo
        assert table[0]["team"] == "Flamengo"

    # Scenario: Champion lookup
    def test_champion_2019(self, sd: SoccerData):
        champ = champion(sd, "Brasileirão", 2019)
        assert champ is not None
        assert champ["champion"] == "Flamengo"

    # Scenario: Relegated teams
    def test_relegated_2019(self, sd: SoccerData):
        rel = relegated(sd, "Brasileirão", 2019, n=4)
        assert len(rel) == 4
        # Relegated teams should be distinct
        assert len(set(rel)) == 4


# ---------------------------------------------------------------------------
# Feature: Statistical Analysis
# ---------------------------------------------------------------------------

class TestStatisticalAnalysis:
    # Scenario: Biggest wins return sorted by margin
    def test_biggest_wins(self, sd: SoccerData):
        wins = biggest_wins(sd, n=5)
        assert len(wins) <= 5
        for w in wins:
            assert w["margin"] > 0
        margins = [w["margin"] for w in wins]
        assert margins == sorted(margins, reverse=True)

    # Scenario: Average goals per match
    def test_avg_goals(self, sd: SoccerData):
        agg = avg_goals(sd, competition="Brasileirão")
        assert agg["matches"] > 0
        assert 1.0 < agg["avg_goals_per_match"] < 6.0
        assert 0.0 <= agg["home_win_rate"] <= 1.0
        # Home advantage: home win rate typically > away win rate
        assert agg["home_win_rate"] > agg["away_win_rate"]

    # Scenario: Best home record ranking
    def test_best_home_record(self, sd: SoccerData):
        ranking = best_home_record(sd, competition="Brasileirão", season=2019, min_matches=5)
        assert len(ranking) > 0
        rates = [r["win_rate"] for r in ranking]
        assert rates == sorted(rates, reverse=True)


# ---------------------------------------------------------------------------
# Feature: Player Queries
# ---------------------------------------------------------------------------

class TestPlayerQueries:
    # Scenario: Search Brazilian players
    def test_brazilian_players(self, sd: SoccerData):
        players = search_players(sd, nationality="Brazil", limit=10)
        assert len(players) > 0
        for p in players:
            assert "Brazil" in p["nationality"]
        # Sorted by overall desc
        overalls = [p["overall"] for p in players]
        assert overalls == sorted(overalls, reverse=True)

    # Scenario: Top Brazilian players helper
    def test_top_brazilian_players(self, sd: SoccerData):
        top = top_brazilian_players(sd, n=5)
        assert len(top) == 5
        assert top[0]["overall"] >= top[-1]["overall"]

    # Scenario: Search by name
    def test_search_by_name(self, sd: SoccerData):
        # Neymar should be findable
        results = search_players(sd, name="Neymar")
        assert any("Neymar" in p["name"] for p in results)

    # Scenario: Filter by club
    def test_players_at_club(self, sd: SoccerData):
        players = players_at_club(sd, "Flamengo", limit=50)
        # The FIFA dataset may not have many Brazilian-club players, but
        # the call must succeed and return a list.
        assert isinstance(players, list)

    # Scenario: Filter by position
    def test_filter_by_position(self, sd: SoccerData):
        forwards = search_players(sd, position="ST", limit=20)
        for p in forwards:
            assert "ST" in p["position"]

    # Scenario: min_overall filter
    def test_min_overall(self, sd: SoccerData):
        players = search_players(sd, min_overall=85, limit=50)
        for p in players:
            assert p["overall"] >= 85


# ---------------------------------------------------------------------------
# Feature: Relationship Queries (derbies)
# ---------------------------------------------------------------------------

class TestDerbies:
    # Scenario: Derby matches exist in dataset
    def test_derbies_exist(self, sd: SoccerData):
        d = derbies(sd)
        assert len(d) > 0
        # Fla-Flu should be present somewhere
        pairs = [(m["home_team"], m["away_team"]) for m in d]
        flat = {t for pair in pairs for t in pair}
        assert "Flamengo" in flat or "Fluminense" in flat

    # Scenario: Derby filter by season
    def test_derbies_2022(self, sd: SoccerData):
        d = derbies(sd, season=2022)
        for m in d:
            assert m["season"] == 2022
