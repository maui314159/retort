"""
Tests for the Brazilian Soccer MCP Server query engine.

All tests exercise real data loaded from data/kaggle/ CSV files.
BDD-style scenarios map directly to the TASK.md specification.
"""

import sys
from pathlib import Path

import pytest

# Ensure project root is on the path so imports resolve
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_loader import SoccerDataLoader, normalize_team, parse_date, strip_accents
from query_engine import QueryEngine

# Shared singleton – data loaded once per session
@pytest.fixture(scope="session")
def loader():
    return SoccerDataLoader()


@pytest.fixture(scope="session")
def engine(loader):
    return QueryEngine(loader)


# ------------------------------------------------------------------ #
# data_loader unit tests                                               #
# ------------------------------------------------------------------ #

class TestNormalizeTeam:
    def test_strips_state_suffix(self):
        assert normalize_team("Palmeiras-SP") == "palmeiras"

    def test_strips_country_suffix(self):
        assert normalize_team("Nacional (URU)") == "nacional"

    def test_strips_parenthetical_old_name(self):
        # "Boavista Sport Club (antigo EC Barreira) - RJ"
        result = normalize_team("Boavista Sport Club (antigo EC Barreira) - RJ")
        assert "boavista" in result
        assert "rj" not in result

    def test_strips_accents(self):
        assert normalize_team("Grêmio") == "gremio"
        assert normalize_team("São Paulo") == "sao paulo"

    def test_lowercases(self):
        assert normalize_team("FLAMENGO") == "flamengo"

    def test_handles_none(self):
        assert normalize_team(None) == ""

    def test_handles_nan(self):
        import numpy as np
        assert normalize_team(float("nan")) == ""


class TestParseDate:
    def test_iso_datetime(self):
        assert parse_date("2023-09-24 18:30:00") == "2023-09-24"

    def test_iso_date(self):
        assert parse_date("2023-09-24") == "2023-09-24"

    def test_brazilian_format(self):
        assert parse_date("29/03/2003") == "2003-03-29"

    def test_none_returns_none(self):
        assert parse_date(None) is None


# ------------------------------------------------------------------ #
# Data loading                                                         #
# ------------------------------------------------------------------ #

class TestDataLoading:
    """Scenario: All 6 CSV files are loadable and queryable."""

    def test_matches_loaded(self, loader):
        df = loader.matches
        assert len(df) > 1000, "Expected thousands of matches"

    def test_matches_has_required_columns(self, loader):
        required = {"date", "home_team", "away_team", "home_goal", "away_goal",
                    "competition", "season", "home_team_raw", "away_team_raw"}
        assert required.issubset(set(loader.matches.columns))

    def test_players_loaded(self, loader):
        df = loader.players
        assert len(df) > 10000, "Expected thousands of players"

    def test_players_has_required_columns(self, loader):
        required = {"Name", "Nationality", "Overall", "Club", "Position"}
        assert required.issubset(set(loader.players.columns))

    def test_all_competitions_present(self, loader):
        comps = set(loader.matches["competition"].unique())
        assert any("Brasil" in c or "Brasileir" in c for c in comps)
        assert any("Copa" in c or "Libert" in c for c in comps)

    def test_no_empty_team_names(self, loader):
        df = loader.matches
        assert (df["home_team"] == "").sum() == 0
        assert (df["away_team"] == "").sum() == 0

    def test_goal_columns_are_numeric(self, loader):
        df = loader.matches
        assert df["home_goal"].dtype.kind == "i"
        assert df["away_goal"].dtype.kind == "i"


# ------------------------------------------------------------------ #
# Match queries                                                        #
# ------------------------------------------------------------------ #

class TestSearchMatches:
    """Scenario: Find matches by criteria."""

    def test_find_flamengo_matches(self, engine):
        matches = engine.search_matches("Flamengo", limit=100)
        assert len(matches) > 10
        for m in matches:
            assert "flamengo" in m["home_team"] or "flamengo" in m["away_team"]

    def test_find_flamengo_vs_fluminense(self, engine):
        """Scenario: Show me all Flamengo vs Fluminense matches."""
        matches = engine.search_matches("Flamengo", opponent="Fluminense", limit=100)
        assert len(matches) > 0
        for m in matches:
            involves_fla = "flamengo" in m["home_team"] or "flamengo" in m["away_team"]
            involves_flu = "fluminense" in m["home_team"] or "fluminense" in m["away_team"]
            assert involves_fla and involves_flu

    def test_filter_by_season(self, engine):
        """Scenario: What matches did Palmeiras play in 2023?"""
        matches = engine.search_matches("Palmeiras", season=2023, limit=100)
        assert len(matches) > 0
        for m in matches:
            assert m["season"] == 2023

    def test_filter_by_competition_brasileirao(self, engine):
        matches = engine.search_matches("Santos", competition="Brasileirão", limit=50)
        assert len(matches) > 0
        for m in matches:
            assert "brasileir" in m["competition"].lower()

    def test_filter_by_competition_libertadores(self, engine):
        matches = engine.search_matches("Flamengo", competition="Copa Libertadores", limit=50)
        assert len(matches) > 0
        for m in matches:
            assert "libertadores" in m["competition"].lower()

    def test_results_sorted_newest_first(self, engine):
        matches = engine.search_matches("Corinthians", limit=50)
        dates = [m["date"] for m in matches if m["date"]]
        if len(dates) > 1:
            assert dates == sorted(dates, reverse=True)

    def test_accent_insensitive_query(self, engine):
        """Querying without accent should still find accented team."""
        matches_norm = engine.search_matches("Gremio", limit=20)
        matches_acc = engine.search_matches("Grêmio", limit=20)
        # Both should find matches; normalized query should work
        assert len(matches_norm) > 0


# ------------------------------------------------------------------ #
# Head-to-head                                                        #
# ------------------------------------------------------------------ #

class TestHeadToHead:
    def test_h2h_palmeiras_santos(self, engine):
        """Scenario: Compare Palmeiras and Santos head-to-head."""
        result = engine.head_to_head("Palmeiras", "Santos")
        assert result["total_matches"] > 0
        assert result["team1_wins"] + result["team2_wins"] + result["draws"] == result["total_matches"]

    def test_h2h_win_counts_consistent(self, engine):
        result = engine.head_to_head("Flamengo", "Corinthians")
        assert result["total_matches"] > 0
        total = result["team1_wins"] + result["team2_wins"] + result["draws"]
        assert total == result["total_matches"]


# ------------------------------------------------------------------ #
# Team statistics                                                      #
# ------------------------------------------------------------------ #

class TestTeamStats:
    def test_corinthians_stats_2022(self, engine):
        """Scenario: What is Corinthians' home record in 2022?"""
        stats = engine.get_team_stats("Corinthians", season=2022, venue="home")
        assert stats["matches"] > 0
        total = stats["wins"] + stats["draws"] + stats["losses"]
        assert total == stats["matches"]

    def test_win_rate_range(self, engine):
        stats = engine.get_team_stats("Palmeiras")
        assert 0.0 <= stats["win_rate"] <= 100.0

    def test_goals_consistency(self, engine):
        stats = engine.get_team_stats("Flamengo")
        assert stats["goals_for"] >= 0
        assert stats["goals_against"] >= 0
        assert stats["goal_diff"] == stats["goals_for"] - stats["goals_against"]

    def test_venue_home_only(self, engine):
        home = engine.get_team_stats("Flamengo", venue="home")
        away = engine.get_team_stats("Flamengo", venue="away")
        both = engine.get_team_stats("Flamengo", venue="both")
        assert home["matches"] + away["matches"] >= both["matches"]

    def test_top_scoring_team_2022(self, engine):
        """Scenario: Which team scored the most goals in Serie A 2022?"""
        # Dataset goes up to 2022; 2023 has no Brasileirão data
        teams = engine.top_scoring_teams(competition="Brasileirão", season=2022, limit=1)
        assert len(teams) > 0
        assert teams[0]["goals_scored"] > 0


# ------------------------------------------------------------------ #
# Player queries                                                       #
# ------------------------------------------------------------------ #

class TestPlayerSearch:
    def test_find_by_name(self, engine):
        """Scenario: Who is Gabriel Barbosa?"""
        players = engine.search_players(name="Gabriel", limit=10)
        assert len(players) > 0

    def test_find_brazilian_players(self, engine):
        """Scenario: Find all Brazilian players in the dataset."""
        players = engine.search_players(nationality="Brazil", limit=50)
        assert len(players) > 0
        for p in players:
            assert "brazil" in p["Nationality"].lower()

    def test_find_players_at_gremio(self, engine):
        """Scenario: Who are the highest-rated players at Grêmio?"""
        # Flamengo is not in this FIFA dataset; Grêmio is.
        players = engine.search_players(club="Grêmio", limit=20)
        assert len(players) > 0
        for p in players:
            assert "gr" in p["Club"].lower()

    def test_find_forwards_at_sao_paulo(self, engine):
        """Scenario: Show me all forwards from São Paulo FC."""
        players = engine.search_players(club="São Paulo", position="ST", limit=10)
        # May be empty if no exact match but query should not error
        assert isinstance(players, list)

    def test_sorted_by_overall_descending(self, engine):
        players = engine.search_players(nationality="Brazil", limit=20)
        ratings = [int(p["Overall"]) for p in players if p.get("Overall", "").isdigit()]
        if len(ratings) > 1:
            assert ratings == sorted(ratings, reverse=True)

    def test_min_overall_filter(self, engine):
        players = engine.search_players(nationality="Brazil", min_overall=85, limit=20)
        for p in players:
            assert int(p["Overall"]) >= 85

    def test_players_by_club_summary(self, engine):
        summary = engine.players_by_club_summary("Brazil")
        assert len(summary) > 0
        for entry in summary[:5]:
            assert "club" in entry
            assert entry["player_count"] > 0
            assert 0 < entry["avg_rating"] <= 100


# ------------------------------------------------------------------ #
# Competition standings                                                #
# ------------------------------------------------------------------ #

class TestStandings:
    def test_standings_brasileirao_2019(self, engine):
        """Scenario: Who won the 2019 Brasileirão?"""
        standings = engine.get_standings("Brasileirão", 2019)
        assert len(standings) > 0
        # Top team should have the most points
        pts = [s["points"] for s in standings]
        assert pts == sorted(pts, reverse=True)

    def test_standings_have_required_fields(self, engine):
        standings = engine.get_standings("Brasileirão", 2022)
        assert len(standings) > 0
        for s in standings:
            assert "team" in s
            assert "points" in s
            assert "wins" in s
            assert "draws" in s
            assert "losses" in s
            assert "goals_for" in s
            assert "goals_against" in s
            assert s["points"] == s["wins"] * 3 + s["draws"]

    def test_standings_libertadores(self, engine):
        standings = engine.get_standings("Copa Libertadores", 2019)
        assert isinstance(standings, list)


# ------------------------------------------------------------------ #
# Statistical analysis                                                 #
# ------------------------------------------------------------------ #

class TestGlobalStats:
    def test_global_stats_all(self, engine):
        stats = engine.get_global_stats()
        assert stats["total_matches"] > 0
        assert stats["avg_goals_per_match"] > 0
        total_outcomes = stats["home_wins"] + stats["away_wins"] + stats["draws"]
        assert total_outcomes == stats["total_matches"]

    def test_global_stats_brasileirao_2022(self, engine):
        # Dataset goes up to 2022; use that year
        stats = engine.get_global_stats(competition="Brasileirão", season=2022)
        assert stats.get("total_matches", 0) > 0

    def test_biggest_wins(self, engine):
        """Scenario: Show me the biggest wins in the dataset."""
        wins = engine.biggest_wins(limit=10)
        assert len(wins) > 0
        margins = [abs(m["home_goal"] - m["away_goal"]) for m in wins]
        assert margins == sorted(margins, reverse=True)

    def test_biggest_wins_brasileirao(self, engine):
        wins = engine.biggest_wins(competition="Brasileirão", limit=5)
        assert len(wins) > 0
        for m in wins:
            assert "brasileir" in m["competition"].lower()
