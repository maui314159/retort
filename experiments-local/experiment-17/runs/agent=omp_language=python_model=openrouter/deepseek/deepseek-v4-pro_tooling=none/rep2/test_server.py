"""
BDD-style tests for the Brazilian Soccer MCP Server.

Uses pytest with Given/When/Then structured test functions.
Tests cover match searches, team stats, head-to-head, player search,
competition standings, and statistical analysis.

Invokes tool functions via asyncio.run() to keep tests deterministic.
"""

from __future__ import annotations

import asyncio
import json
import pytest

from data_loader import load_all, clear_cache, normalize_team_name
from server import (
    soccer_search_matches,
    soccer_team_stats,
    soccer_head_to_head,
    soccer_search_players,
    soccer_competition_standings,
    soccer_stats_analysis,
    MatchSearchInput,
    TeamStatsInput,
    HeadToHeadInput,
    PlayerSearchInput,
    StandingsInput,
    StatsAnalysisInput,
)


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


# =========================================================================
# Team name normalization
# =========================================================================

class TestTeamNormalization:
    """Team name normalization across datasets."""

    def test_strips_state_suffix(self):
        assert normalize_team_name("Palmeiras-SP") == "Palmeiras"
        assert normalize_team_name("Flamengo-RJ") == "Flamengo"
        assert normalize_team_name("Corinthians-SP") == "Corinthians"

    def test_normalizes_accented_names(self):
        assert normalize_team_name("São Paulo") == "São Paulo"
        assert normalize_team_name("sao paulo") == "São Paulo"
        assert normalize_team_name("Grêmio") == "Grêmio"
        assert normalize_team_name("gremio") == "Grêmio"

    def test_handles_atletico_variations(self):
        assert normalize_team_name("Athletico Paranaense") == "Athletico-PR"
        assert normalize_team_name("Atlético-MG") == "Atlético-MG"
        assert normalize_team_name("Atletico Mineiro") == "Atlético-MG"

    def test_handles_america_variations(self):
        assert normalize_team_name("America MG") == "América-MG"
        assert normalize_team_name("América-MG") == "América-MG"


# =========================================================================
# Match Queries
# =========================================================================

class TestMatchSearch:
    """Feature: Match Queries — find matches by team, date, competition, season."""

    def test_search_by_team(self):
        inp = MatchSearchInput(team="flamengo", limit=5, response_format="json")
        result = json.loads(_run(soccer_search_matches(inp)))
        assert result["total"] > 100
        for m in result["matches"]:
            teams = {m["home_team"].lower(), m["away_team"].lower()}
            assert "flamengo" in teams
            assert m["score"]
            assert m["date"]
            assert m["competition"]

    def test_search_by_team_and_opponent(self):
        inp = MatchSearchInput(team="flamengo", opponent="fluminense", response_format="json")
        result = json.loads(_run(soccer_search_matches(inp)))
        for m in result["matches"]:
            teams = {m["home_team"].lower(), m["away_team"].lower()}
            assert teams == {"flamengo", "fluminense"}

    def test_search_by_competition(self):
        inp = MatchSearchInput(competition="Brasileirão", limit=20, response_format="json")
        result = json.loads(_run(soccer_search_matches(inp)))
        assert result["total"] > 100
        for m in result["matches"]:
            assert "brasileir" in m["competition"].lower()

    def test_search_by_season(self):
        inp = MatchSearchInput(season=2022, limit=20, response_format="json")
        result = json.loads(_run(soccer_search_matches(inp)))
        assert result["total"] > 0
        for m in result["matches"]:
            assert m["season"] == 2022

    def test_search_by_date_range(self):
        inp = MatchSearchInput(date_from="2022-04-01", date_to="2022-04-30", limit=20, response_format="json")
        result_raw = _run(soccer_search_matches(inp))
        result = json.loads(result_raw)
        assert result["total"] > 0
        for m in result["matches"]:
            assert m["date"] >= "2022-04-01"
            assert m["date"] <= "2022-04-30"
        inp = MatchSearchInput(team="zzzz_nonexistent_team_12345", response_format="json")
        result = _run(soccer_search_matches(inp))
        assert "No matches found" in result

    def test_markdown_output(self):
        result = _run(soccer_search_matches(MatchSearchInput(team="flamengo", limit=2)))
        assert result.startswith("#")
        assert "Flamengo" in result


# =========================================================================
# Team Statistics
# =========================================================================

class TestTeamStats:
    """Feature: Team Statistics — wins, losses, draws, goals."""

    def test_team_stats_basic(self):
        inp = TeamStatsInput(team="flamengo", response_format="json")
        result = json.loads(_run(soccer_team_stats(inp)))
        assert result["matches"] > 0
        assert result["wins"] + result["draws"] + result["losses"] == result["matches"]
        assert result["goals_for"] >= 0
        assert result["goals_against"] >= 0
        assert result["goal_difference"] == result["goals_for"] - result["goals_against"]
        assert 0 <= result["win_rate_pct"] <= 100

    def test_team_stats_by_competition(self):
        inp = TeamStatsInput(team="flamengo", competition="Brasileirão", response_format="json")
        result = json.loads(_run(soccer_team_stats(inp)))
        assert result["matches"] > 0
        all_inp = TeamStatsInput(team="flamengo", response_format="json")
        all_result = json.loads(_run(soccer_team_stats(all_inp)))
        assert result["matches"] <= all_result["matches"]

    def test_team_stats_by_season(self):
        inp = TeamStatsInput(team="palmeiras", season=2022, response_format="json")
        result = json.loads(_run(soccer_team_stats(inp)))
        assert result["matches"] > 0

    def test_team_stats_home_only(self):
        inp = TeamStatsInput(team="corinthians", home_away="home", response_format="json")
        result = json.loads(_run(soccer_team_stats(inp)))
        assert result["matches"] > 0

    def test_team_stats_away_only(self):
        inp = TeamStatsInput(team="corinthians", home_away="away", response_format="json")
        result = json.loads(_run(soccer_team_stats(inp)))
        assert result["matches"] > 0

    def test_unknown_team(self):
        inp = TeamStatsInput(team="zzzz_nonexistent")
        result = _run(soccer_team_stats(inp))
        assert "No matches found" in result

    def test_markdown_output(self):
        result = _run(soccer_team_stats(TeamStatsInput(team="flamengo")))
        assert result.startswith("#")


# =========================================================================
# Head-to-Head
# =========================================================================

class TestHeadToHead:
    """Feature: Head-to-Head comparisons between two teams."""

    def test_fla_flu_derby(self):
        inp = HeadToHeadInput(team_a="flamengo", team_b="fluminense", response_format="json")
        result = json.loads(_run(soccer_head_to_head(inp)))
        assert result["total_matches"] > 0
        assert result["team_a_wins"] + result["team_b_wins"] + result["draws"] == result["total_matches"]
        assert len(result["recent_matches"]) > 0

    def test_classic_rivalry(self):
        inp = HeadToHeadInput(team_a="corinthians", team_b="palmeiras", response_format="json")
        result = json.loads(_run(soccer_head_to_head(inp)))
        assert result["total_matches"] > 0
        assert result["team_a_goals"] >= 0
        assert result["team_b_goals"] >= 0

    def test_h2h_with_competition_filter(self):
        inp_all = HeadToHeadInput(team_a="são paulo", team_b="corinthians", response_format="json")
        all_result = json.loads(_run(soccer_head_to_head(inp_all)))
        inp_comp = HeadToHeadInput(team_a="são paulo", team_b="corinthians",
                                    competition="Brasileirão", response_format="json")
        comp_result = json.loads(_run(soccer_head_to_head(inp_comp)))
        if all_result["total_matches"] > 0:
            assert comp_result["total_matches"] <= all_result["total_matches"]

    def test_no_h2h_matches(self):
        inp = HeadToHeadInput(team_a="zzzz_team_x", team_b="zzzz_team_y")
        result = _run(soccer_head_to_head(inp))
        assert "No head-to-head matches found" in result

    def test_markdown_output(self):
        result = _run(soccer_head_to_head(HeadToHeadInput(team_a="flamengo", team_b="fluminense")))
        assert result.startswith("#")


# =========================================================================
# Player Search
# =========================================================================

class TestPlayerSearch:
    """Feature: Player queries — search by name, nationality, club, position."""

    def test_search_by_name(self):
        inp = PlayerSearchInput(name="Neymar", response_format="json")
        result = json.loads(_run(soccer_search_players(inp)))
        assert result["total"] >= 1
        names = [p["name"].lower() for p in result["players"]]
        assert any("neymar" in n for n in names)

    def test_search_by_nationality(self):
        inp = PlayerSearchInput(nationality="Brazil", limit=10, response_format="json")
        result = json.loads(_run(soccer_search_players(inp)))
        assert result["total"] > 100
        for p in result["players"]:
            assert p["nationality"].lower() == "brazil"

    def test_search_by_club(self):
        inp = PlayerSearchInput(club="Barcelona", limit=10, response_format="json")
        result = json.loads(_run(soccer_search_players(inp)))
        assert result["total"] > 0
        for p in result["players"]:
            assert "barcelona" in p["club"].lower()

    def test_search_by_position(self):
        inp = PlayerSearchInput(position="GK", limit=10, response_format="json")
        result = json.loads(_run(soccer_search_players(inp)))
        assert result["total"] > 0
        for p in result["players"]:
            assert "GK" in p["position"]

    def test_search_by_rating_range(self):
        inp = PlayerSearchInput(min_overall=90, sort_by="overall", sort_desc=True,
                                 limit=10, response_format="json")
        result = json.loads(_run(soccer_search_players(inp)))
        assert result["total"] > 0
        for p in result["players"]:
            assert p["overall"] >= 90

    def test_top_brazilian_players(self):
        inp = PlayerSearchInput(nationality="Brazil", sort_by="overall", sort_desc=True,
                                 limit=5, response_format="json")
        result = json.loads(_run(soccer_search_players(inp)))
        assert len(result["players"]) > 0
        assert result["players"][0]["overall"] >= 85

    def test_no_players_found(self):
        inp = PlayerSearchInput(name="zzzz_nonexistent_player_xyz")
        result = _run(soccer_search_players(inp))
        assert "No players found" in result

    def test_markdown_output(self):
        result = _run(soccer_search_players(PlayerSearchInput(nationality="Brazil", limit=2)))
        assert result.startswith("#")


# =========================================================================
# Competition Standings
# =========================================================================

class TestCompetitionStandings:
    """Feature: Competition standings from match results."""

    def test_brasileirao_2022_standings(self):
        inp = StandingsInput(competition="Brasileirão", season=2022, limit=20, response_format="json")
        result = json.loads(_run(soccer_competition_standings(inp)))
        assert len(result["standings"]) > 0
        pts = [t["points"] for t in result["standings"]]
        assert pts == sorted(pts, reverse=True)
        for t in result["standings"]:
            assert t["played"] == t["wins"] + t["draws"] + t["losses"]
            assert t["goal_difference"] == t["goals_for"] - t["goals_against"]
            assert t["points"] == t["wins"] * 3 + t["draws"]

    def test_brasileirao_2019_standings(self):
        inp = StandingsInput(competition="Brasileirão", season=2019, limit=20, response_format="json")
        result = json.loads(_run(soccer_competition_standings(inp)))
        assert len(result["standings"]) > 0
        assert result["standings"][0]["position"] == 1

    def test_unknown_competition(self):
        inp = StandingsInput(competition="zzzz_fake_league", season=2022)
        result = _run(soccer_competition_standings(inp))
        assert "No matches found" in result

    def test_markdown_output(self):
        result = _run(soccer_competition_standings(StandingsInput(season=2022)))
        assert result.startswith("#")


# =========================================================================
# Statistical Analysis
# =========================================================================

class TestStatisticalAnalysis:
    """Feature: Statistical analysis of match data."""

    def test_averages(self):
        inp = StatsAnalysisInput(analysis_type="averages", response_format="json")
        result = json.loads(_run(soccer_stats_analysis(inp)))
        assert result["total_matches"] > 1000
        assert result["avg_goals_per_match"] > 0
        assert 0 <= result["home_win_pct"] <= 100
        assert 0 <= result["away_win_pct"] <= 100
        assert 0 <= result["draw_pct"] <= 100

    def test_biggest_wins(self):
        inp = StatsAnalysisInput(analysis_type="biggest_wins", limit=10, response_format="json")
        result = json.loads(_run(soccer_stats_analysis(inp)))
        assert len(result["biggest_wins"]) > 0
        diffs = [m["difference"] for m in result["biggest_wins"]]
        assert diffs == sorted(diffs, reverse=True)

    def test_home_away_analysis(self):
        inp = StatsAnalysisInput(analysis_type="home_away", response_format="json")
        result = json.loads(_run(soccer_stats_analysis(inp)))
        assert len(result["best_home"]) > 0
        assert len(result["best_away"]) > 0

    def test_goal_trends(self):
        inp = StatsAnalysisInput(analysis_type="goal_trends", response_format="json")
        result = json.loads(_run(soccer_stats_analysis(inp)))
        assert len(result["goal_trends"]) > 0
        for t in result["goal_trends"]:
            assert t["matches"] > 0

    def test_top_scorers(self):
        inp = StatsAnalysisInput(analysis_type="top_scorers", limit=10, response_format="json")
        result = json.loads(_run(soccer_stats_analysis(inp)))
        assert len(result["top_scoring_teams"]) > 0
        goals = [t["goals"] for t in result["top_scoring_teams"]]
        assert goals == sorted(goals, reverse=True)

    def test_filtered_analysis(self):
        inp = StatsAnalysisInput(analysis_type="averages", competition="Brasileirão",
                                  response_format="json")
        result = json.loads(_run(soccer_stats_analysis(inp)))
        assert result["total_matches"] > 0

    def test_markdown_output(self):
        result = _run(soccer_stats_analysis(StatsAnalysisInput(analysis_type="averages")))
        assert result.startswith("#")


# =========================================================================
# Cross-feature tests
# =========================================================================

class TestCrossFeature:
    """Integration tests spanning multiple tools."""

    def test_data_consistency(self):
        inp = StandingsInput(competition="Brasileirão", season=2022, limit=1, response_format="json")
        standings = json.loads(_run(soccer_competition_standings(inp)))
        assert len(standings["standings"]) > 0

    def test_markdown_all_tools(self):
        """All tools produce markdown output by default."""
        r1 = _run(soccer_search_matches(MatchSearchInput(team="flamengo", limit=2)))
        assert r1.startswith("#")
        r2 = _run(soccer_team_stats(TeamStatsInput(team="flamengo")))
        assert r2.startswith("#")
        r3 = _run(soccer_search_players(PlayerSearchInput(nationality="Brazil", limit=2)))
        assert r3.startswith("#")
        r4 = _run(soccer_competition_standings(StandingsInput(season=2022)))
        assert r4.startswith("#")
        r5 = _run(soccer_stats_analysis(StatsAnalysisInput(analysis_type="averages")))
        assert r5.startswith("#")
