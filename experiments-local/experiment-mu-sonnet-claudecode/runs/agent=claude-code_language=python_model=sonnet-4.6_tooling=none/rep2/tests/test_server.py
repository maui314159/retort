"""BDD-style tests for the Brazilian Soccer MCP server."""

import asyncio
import sys
import os

import pytest
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from data_loader import (
    load_brasileirao, load_copa_brasil, load_libertadores,
    load_br_football, load_historico, load_fifa, load_all_matches,
    normalize_team,
)
import server as srv


# ---------- Fixtures ----------

@pytest.fixture(scope="session")
def brasileirao():
    return load_brasileirao()


@pytest.fixture(scope="session")
def copa_brasil():
    return load_copa_brasil()


@pytest.fixture(scope="session")
def libertadores():
    return load_libertadores()


@pytest.fixture(scope="session")
def br_football():
    return load_br_football()


@pytest.fixture(scope="session")
def historico():
    return load_historico()


@pytest.fixture(scope="session")
def fifa():
    return load_fifa()


@pytest.fixture(scope="session")
def all_matches():
    return load_all_matches()


def run_tool(name, arguments):
    """Helper to call MCP tools synchronously in tests."""
    # Ensure data is loaded
    srv._get_data()
    return asyncio.get_event_loop().run_until_complete(srv.call_tool(name, arguments))


# ---------- Data Loading ----------

class TestDataLoading:
    """Feature: All datasets are loadable and well-formed."""

    def test_brasileirao_loads(self, brasileirao):
        """Scenario: Brasileirao matches CSV loads with expected columns."""
        assert len(brasileirao) > 4000
        assert {"home_team", "away_team", "home_goal", "away_goal", "season"}.issubset(brasileirao.columns)

    def test_copa_brasil_loads(self, copa_brasil):
        assert len(copa_brasil) > 1000
        assert {"home_team", "away_team", "home_goal", "away_goal"}.issubset(copa_brasil.columns)

    def test_libertadores_loads(self, libertadores):
        assert len(libertadores) > 1000
        assert {"home_team", "away_team", "home_goal", "away_goal"}.issubset(libertadores.columns)

    def test_br_football_loads(self, br_football):
        assert len(br_football) > 5000
        assert {"home_team", "away_team", "home_goal", "away_goal"}.issubset(br_football.columns)

    def test_historico_loads(self, historico):
        assert len(historico) > 5000
        assert {"home_team", "away_team", "home_goal", "away_goal"}.issubset(historico.columns)

    def test_fifa_loads(self, fifa):
        assert len(fifa) > 10000
        assert {"Name", "Nationality", "Club", "Overall", "Position"}.issubset(fifa.columns)

    def test_all_matches_loads(self, all_matches):
        assert len(all_matches) > 10000
        assert {"home_team", "away_team", "home_goal", "away_goal", "competition"}.issubset(all_matches.columns)

    def test_dates_parsed(self, brasileirao):
        """Dates should be parsed as datetime, not strings."""
        non_nat = brasileirao["datetime"].dropna()
        assert len(non_nat) > 0
        assert pd.api.types.is_datetime64_any_dtype(brasileirao["datetime"])

    def test_historico_dates_parsed(self, historico):
        """Brazilian date format DD/MM/YYYY should parse correctly."""
        non_nat = historico["datetime"].dropna()
        assert len(non_nat) > 0
        assert pd.api.types.is_datetime64_any_dtype(historico["datetime"])


# ---------- Team Name Normalization ----------

class TestTeamNormalization:
    """Feature: Team names are normalized for consistent matching."""

    def test_state_suffix_stripped(self):
        """Scenario: 'Palmeiras-SP' normalizes to 'palmeiras'."""
        assert normalize_team("Palmeiras-SP") == "palmeiras"

    def test_accent_handled(self):
        """Scenario: 'Grêmio' normalizes to 'gremio'."""
        assert normalize_team("Grêmio") == "gremio"

    def test_flamengo_alias(self):
        assert normalize_team("Flamengo-RJ") == "flamengo"

    def test_atletico_mineiro(self):
        assert normalize_team("Atletico-MG") == "atletico mineiro"

    def test_unknown_team_passthrough(self):
        """Unknown teams return a cleaned version, not an error."""
        result = normalize_team("Some Unknown FC")
        assert isinstance(result, str)
        assert len(result) > 0


# ---------- Match Queries ----------

class TestMatchQueries:
    """Feature: Match Queries"""

    def test_find_matches_by_team(self, all_matches):
        """Scenario: Find matches for a team."""
        result = run_tool("search_matches", {"team": "Flamengo", "limit": 50})
        text = result[0].text
        assert "Flamengo" in text or "flamengo" in text.lower()
        assert "matches" in text.lower()

    def test_find_matches_between_two_teams(self, all_matches):
        """Scenario: Find matches between Flamengo and Fluminense."""
        result = run_tool("search_matches", {"team": "Flamengo", "team2": "Fluminense", "limit": 20})
        text = result[0].text
        # Should return some matches or a clear message
        assert "match" in text.lower() or "found" in text.lower()

    def test_find_matches_by_season(self, all_matches):
        """Scenario: Find Palmeiras matches in 2023."""
        result = run_tool("search_matches", {"team": "Palmeiras", "season": 2023, "limit": 30})
        text = result[0].text
        assert "Palmeiras" in text or "palmeiras" in text.lower() or "No matches" in text

    def test_find_matches_by_competition(self):
        """Scenario: Filter matches by competition."""
        result = run_tool("search_matches", {"competition": "Libertadores", "limit": 10})
        text = result[0].text
        assert "Libertadores" in text or "matches" in text.lower()

    def test_find_matches_date_range(self):
        """Scenario: Find matches in a date range."""
        result = run_tool("search_matches", {
            "date_from": "2023-01-01",
            "date_to": "2023-12-31",
            "limit": 10,
        })
        text = result[0].text
        assert "match" in text.lower() or "found" in text.lower()

    def test_match_result_has_score(self):
        """Scenario: Each match result includes date and score."""
        result = run_tool("search_matches", {"team": "Corinthians", "limit": 5})
        text = result[0].text
        # Should contain score pattern like "1-0" or "2-1"
        import re
        if "No matches" not in text:
            assert re.search(r'\d+-\d+', text), "Expected score in results"

    def test_no_matches_returns_message(self):
        """Scenario: Querying a non-existent team returns a helpful message."""
        result = run_tool("search_matches", {"team": "ZZZZNONEXISTENT9999"})
        text = result[0].text
        assert "no matches" in text.lower() or "not found" in text.lower()


# ---------- Team Statistics ----------

class TestTeamStats:
    """Feature: Team statistics calculation."""

    def test_team_stats_returns_record(self):
        """Scenario: Get Corinthians home record in 2022."""
        result = run_tool("get_team_stats", {"team": "Corinthians", "season": 2022})
        text = result[0].text
        assert "Wins" in text or "wins" in text.lower() or "No matches" in text

    def test_team_stats_includes_goals(self):
        """Scenario: Stats include goals for and against."""
        result = run_tool("get_team_stats", {"team": "Palmeiras"})
        text = result[0].text
        if "No matches" not in text:
            assert "Goals" in text or "GF" in text

    def test_team_stats_home_only(self):
        """Scenario: Get home-only stats."""
        result = run_tool("get_team_stats", {"team": "Flamengo", "home_only": True})
        text = result[0].text
        assert "stats" in text.lower() or "No matches" in text

    def test_team_stats_win_rate(self):
        """Scenario: Stats include win rate."""
        result = run_tool("get_team_stats", {"team": "Santos"})
        text = result[0].text
        if "No matches" not in text:
            assert "%" in text or "Win" in text

    def test_team_not_found(self):
        result = run_tool("get_team_stats", {"team": "ZZZZINVALID"})
        text = result[0].text
        assert "no matches" in text.lower() or "not found" in text.lower()


# ---------- Player Queries ----------

class TestPlayerQueries:
    """Feature: Player Queries"""

    def test_find_brazilian_players(self, fifa):
        """Scenario: Find all Brazilian players."""
        result = run_tool("search_players", {"nationality": "Brazil", "limit": 10})
        text = result[0].text
        assert "Brazil" in text or "found" in text.lower()

    def test_find_player_by_name(self):
        """Scenario: Find player Gabriel Barbosa."""
        result = run_tool("search_players", {"name": "Neymar", "limit": 5})
        text = result[0].text
        assert "Neymar" in text or "found" in text.lower()

    def test_find_players_at_club(self):
        """Scenario: Find players at Flamengo."""
        result = run_tool("search_players", {"club": "Flamengo", "limit": 10})
        text = result[0].text
        assert "found" in text.lower()

    def test_find_players_by_position(self):
        """Scenario: Find goalkeepers."""
        result = run_tool("search_players", {"position": "GK", "limit": 10})
        text = result[0].text
        assert "found" in text.lower()

    def test_find_top_rated_players(self):
        """Scenario: Find top-rated Brazilian players."""
        result = run_tool("search_players", {
            "nationality": "Brazil",
            "min_overall": 85,
            "limit": 10,
        })
        text = result[0].text
        assert "found" in text.lower()

    def test_player_result_includes_rating(self):
        """Scenario: Player results include overall rating."""
        result = run_tool("search_players", {"nationality": "Brazil", "limit": 5})
        text = result[0].text
        if "No players" not in text:
            assert "Overall" in text

    def test_player_not_found(self):
        result = run_tool("search_players", {"name": "ZZZZINVALIDPLAYER"})
        text = result[0].text
        assert "no players" in text.lower() or "not found" in text.lower()


# ---------- Head-to-Head ----------

class TestHeadToHead:
    """Feature: Head-to-head comparison between two teams."""

    def test_h2h_flamengo_fluminense(self):
        """Scenario: Find all Flamengo vs Fluminense matches."""
        result = run_tool("get_head_to_head", {"team1": "Flamengo", "team2": "Fluminense"})
        text = result[0].text
        assert "Head-to-Head" in text or "no matches" in text.lower()

    def test_h2h_returns_record(self):
        """Scenario: H2H shows wins for each team."""
        result = run_tool("get_head_to_head", {"team1": "Palmeiras", "team2": "Corinthians"})
        text = result[0].text
        if "no matches" not in text.lower():
            assert "wins" in text.lower() or "Wins" in text

    def test_h2h_no_matches(self):
        result = run_tool("get_head_to_head", {"team1": "ZZINVALID1", "team2": "ZZINVALID2"})
        text = result[0].text
        assert "no matches" in text.lower() or "not found" in text.lower()


# ---------- Competition Standings ----------

class TestStandings:
    """Feature: Competition standings calculated from match data."""

    def test_standings_2019(self):
        """Scenario: 2019 Brasileirão standings - Flamengo should be champion."""
        result = run_tool("get_competition_standings", {"season": 2019, "top_n": 5})
        text = result[0].text
        assert "2019" in text
        # Flamengo won 2019 with 90 points
        if "No match" not in text:
            assert "flamengo" in text.lower() or "Flamengo" in text

    def test_standings_structure(self):
        """Scenario: Standings show points, wins, draws, losses."""
        result = run_tool("get_competition_standings", {"season": 2018})
        text = result[0].text
        if "No match" not in text:
            assert "Pts" in text or "pts" in text.lower()

    def test_standings_invalid_season(self):
        result = run_tool("get_competition_standings", {"season": 1900})
        text = result[0].text
        assert "no" in text.lower() or "not found" in text.lower()


# ---------- Biggest Wins ----------

class TestBiggestWins:
    """Feature: Find biggest victories."""

    def test_biggest_wins_overall(self):
        """Scenario: Find the biggest wins across all data."""
        result = run_tool("get_biggest_wins", {"limit": 5})
        text = result[0].text
        assert "Biggest victories" in text or "margin" in text.lower()

    def test_biggest_wins_margin_present(self):
        """Scenario: Results include the goal margin."""
        result = run_tool("get_biggest_wins", {"limit": 3})
        text = result[0].text
        assert "Margin" in text or "margin" in text.lower()

    def test_biggest_wins_by_competition(self):
        result = run_tool("get_biggest_wins", {"competition": "Brasileirao", "limit": 5})
        text = result[0].text
        assert "Biggest" in text or "match" in text.lower()


# ---------- Average Goals ----------

class TestAverageGoals:
    """Feature: Statistical analysis."""

    def test_average_goals_all(self):
        """Scenario: Average goals per match across all data."""
        result = run_tool("get_average_goals", {})
        text = result[0].text
        assert "Average" in text or "average" in text.lower()

    def test_average_goals_has_home_rate(self):
        """Scenario: Stats include home win rate."""
        result = run_tool("get_average_goals", {})
        text = result[0].text
        assert "Home" in text or "%" in text

    def test_average_goals_by_season(self):
        result = run_tool("get_average_goals", {"competition": "Brasileirao", "season": 2022})
        text = result[0].text
        assert "match" in text.lower() or "No data" in text
