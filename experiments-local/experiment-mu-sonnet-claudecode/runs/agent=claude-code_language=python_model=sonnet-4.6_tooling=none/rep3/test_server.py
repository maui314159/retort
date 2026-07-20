"""Tests for the Brazilian Soccer MCP server tools."""

import pytest

import data_loader as dl
from data_loader import normalize_team, team_matches


# ── Normalization ──────────────────────────────────────────────────────────────

class TestNormalization:
    def test_removes_state_suffix(self):
        assert normalize_team("Palmeiras-SP") == "palmeiras"

    def test_handles_lowercase(self):
        assert normalize_team("FLAMENGO") == "flamengo"

    def test_strips_accents(self):
        result = normalize_team("Grêmio")
        assert "gremio" in result

    def test_team_matches_with_suffix(self):
        assert team_matches("Flamengo", "Flamengo-RJ")

    def test_team_matches_case_insensitive(self):
        assert team_matches("palmeiras", "Palmeiras-SP")


# ── Data loading ───────────────────────────────────────────────────────────────

class TestDataLoading:
    def test_brasileirao_loads(self):
        df = dl.load_brasileirao()
        assert len(df) > 0
        assert "home" in df.columns
        assert "away" in df.columns

    def test_copa_brasil_loads(self):
        df = dl.load_copa_brasil()
        assert len(df) > 0

    def test_libertadores_loads(self):
        df = dl.load_libertadores()
        assert len(df) > 0

    def test_br_football_loads(self):
        df = dl.load_br_football()
        assert len(df) > 0

    def test_historico_loads(self):
        df = dl.load_historico()
        assert len(df) > 0

    def test_fifa_loads(self):
        df = dl.load_fifa()
        assert len(df) > 0
        assert "Name" in df.columns
        assert "Overall" in df.columns

    def test_all_matches_loads(self):
        df = dl.load_all_matches()
        assert len(df) > 10000


# ── Match queries ──────────────────────────────────────────────────────────────

class TestFindMatches:
    def test_find_by_team(self):
        results = dl.find_matches(team1="Flamengo")
        assert len(results) > 0
        for r in results:
            assert "flamengo" in r["home_team"].lower() or "flamengo" in r["away_team"].lower()

    def test_find_by_two_teams(self):
        results = dl.find_matches(team1="Flamengo", team2="Fluminense")
        assert len(results) > 0
        for r in results:
            teams = (r["home_team"].lower(), r["away_team"].lower())
            assert any("flamengo" in t for t in teams)
            assert any("fluminense" in t for t in teams)

    def test_find_by_competition(self):
        results = dl.find_matches(competition="Libertadores")
        assert len(results) > 0
        for r in results:
            assert "libertadores" in r["competition"].lower()

    def test_find_by_season(self):
        results = dl.find_matches(season=2019)
        assert len(results) > 0
        for r in results:
            assert r["season"] == 2019

    def test_find_by_date_range(self):
        results = dl.find_matches(date_from="2023-01-01", date_to="2023-12-31")
        assert len(results) > 0

    def test_limit_respected(self):
        results = dl.find_matches(limit=5)
        assert len(results) <= 5

    def test_result_has_required_fields(self):
        results = dl.find_matches(limit=1)
        assert len(results) == 1
        r = results[0]
        assert "date" in r
        assert "home_team" in r
        assert "away_team" in r
        assert "home_goals" in r
        assert "away_goals" in r
        assert "competition" in r

    def test_palmeiras_corinthians_derby(self):
        results = dl.find_matches(team1="Palmeiras", team2="Corinthians")
        assert len(results) > 0


# ── Team statistics ────────────────────────────────────────────────────────────

class TestTeamStats:
    def test_flamengo_stats(self):
        stats = dl.get_team_stats("Flamengo")
        assert stats["matches"] > 0
        assert "wins" in stats
        assert "draws" in stats
        assert "losses" in stats
        assert stats["wins"] + stats["draws"] + stats["losses"] == stats["matches"]

    def test_stats_with_season(self):
        stats = dl.get_team_stats("Palmeiras", season=2022)
        assert stats["season"] == 2022

    def test_stats_with_competition(self):
        stats = dl.get_team_stats("Flamengo", competition="Brasileirao")
        assert stats["matches"] > 0

    def test_home_away_breakdown(self):
        stats = dl.get_team_stats("Santos")
        assert "home" in stats
        assert "away" in stats
        assert stats["home"]["matches"] + stats["away"]["matches"] == stats["matches"]

    def test_win_rate_calculation(self):
        stats = dl.get_team_stats("Corinthians")
        expected = round(stats["wins"] / stats["matches"] * 100, 1)
        assert stats["win_rate"] == expected

    def test_unknown_team_returns_no_matches(self):
        stats = dl.get_team_stats("NonExistentTeamXYZ123")
        assert stats["matches"] == 0


# ── Head-to-head ───────────────────────────────────────────────────────────────

class TestHeadToHead:
    def test_flamengo_fluminense(self):
        h2h = dl.get_head_to_head("Flamengo", "Fluminense")
        assert h2h["total_matches"] > 0
        assert "recent_matches" in h2h

    def test_h2h_win_counts_sum_to_total(self):
        h2h = dl.get_head_to_head("Palmeiras", "Santos")
        t1_wins = h2h.get("Palmeiras_wins", 0)
        t2_wins = h2h.get("Santos_wins", 0)
        draws = h2h["draws"]
        assert t1_wins + t2_wins + draws == h2h["total_matches"]

    def test_h2h_recent_limit(self):
        h2h = dl.get_head_to_head("Flamengo", "Corinthians", limit=5)
        assert len(h2h["recent_matches"]) <= 5

    def test_h2h_match_has_required_fields(self):
        h2h = dl.get_head_to_head("Flamengo", "Fluminense", limit=1)
        if h2h["recent_matches"]:
            m = h2h["recent_matches"][0]
            assert "date" in m
            assert "home_goals" in m
            assert "away_goals" in m


# ── Player queries ─────────────────────────────────────────────────────────────

class TestFindPlayers:
    def test_find_by_nationality(self):
        players = dl.find_players(nationality="Brazil", limit=10)
        assert len(players) > 0
        for p in players:
            assert "brazil" in p["nationality"].lower()

    def test_find_by_name(self):
        players = dl.find_players(name="Neymar")
        assert len(players) > 0

    def test_find_by_club(self):
        players = dl.find_players(club="Barcelona")
        assert len(players) > 0

    def test_find_by_position(self):
        players = dl.find_players(position="GK", nationality="Brazil", limit=5)
        for p in players:
            assert "gk" in p["position"].lower()

    def test_min_overall_filter(self):
        players = dl.find_players(min_overall=85)
        for p in players:
            assert int(p["overall"]) >= 85

    def test_player_has_required_fields(self):
        players = dl.find_players(limit=1)
        assert len(players) == 1
        p = players[0]
        assert "name" in p
        assert "nationality" in p
        assert "overall" in p
        assert "club" in p
        assert "position" in p

    def test_sorted_by_overall(self):
        players = dl.find_players(nationality="Brazil", limit=5)
        ratings = [int(p["overall"]) for p in players if p["overall"].isdigit()]
        assert ratings == sorted(ratings, reverse=True)


# ── Standings ──────────────────────────────────────────────────────────────────

class TestStandings:
    def test_brasileirao_2019(self):
        table = dl.get_standings(2019, "Brasileirao")
        assert len(table) > 0
        assert table[0]["position"] == 1
        # Flamengo won 2019 — should be near top
        top5 = [row["team"] for row in table[:5]]
        assert any("flamengo" in t for t in top5)

    def test_standings_sorted_by_points(self):
        table = dl.get_standings(2018, "Brasileirao")
        if len(table) >= 2:
            assert table[0]["pts"] >= table[1]["pts"]

    def test_standings_has_required_fields(self):
        table = dl.get_standings(2019, "Brasileirao")
        if table:
            row = table[0]
            assert "team" in row
            assert "pts" in row
            assert "W" in row
            assert "D" in row
            assert "L" in row
            assert "GF" in row
            assert "GA" in row

    def test_empty_for_unknown_competition(self):
        table = dl.get_standings(2019, "UnknownLeagueXYZ")
        assert table == []


# ── Biggest wins ───────────────────────────────────────────────────────────────

class TestBiggestWins:
    def test_returns_results(self):
        wins = dl.get_biggest_wins()
        assert len(wins) > 0

    def test_sorted_by_goal_diff(self):
        wins = dl.get_biggest_wins(limit=10)
        diffs = [w["goal_difference"] for w in wins]
        assert diffs == sorted(diffs, reverse=True)

    def test_filter_by_competition(self):
        wins = dl.get_biggest_wins(competition="Brasileirao")
        assert len(wins) > 0

    def test_result_fields(self):
        wins = dl.get_biggest_wins(limit=1)
        w = wins[0]
        assert "home_team" in w
        assert "away_team" in w
        assert "goal_difference" in w
        assert w["goal_difference"] >= 0


# ── Dataset summary ────────────────────────────────────────────────────────────

class TestDatasetSummary:
    def test_overall_summary(self):
        summary = dl.get_competition_summary()
        assert summary["total_matches"] > 10000
        assert summary["avg_goals_per_match"] > 0
        assert summary["home_win_rate"] + summary["away_win_rate"] + summary["draw_rate"] == pytest.approx(100, abs=0.2)

    def test_filtered_summary(self):
        summary = dl.get_competition_summary("Brasileirao")
        assert summary["total_matches"] > 0

    def test_summary_has_seasons(self):
        summary = dl.get_competition_summary()
        assert len(summary["seasons"]) > 5


# ── MCP server tools ───────────────────────────────────────────────────────────

class TestMCPServer:
    def test_server_importable(self):
        import server
        assert server.mcp is not None

    def test_tools_registered(self):
        import asyncio
        import server

        async def _get_tools():
            return await server.mcp.list_tools()

        tools = asyncio.run(_get_tools())
        tool_names = [t.name for t in tools]
        assert "find_matches" in tool_names
        assert "get_team_statistics" in tool_names
        assert "get_head_to_head" in tool_names
        assert "find_players" in tool_names
        assert "get_standings" in tool_names
        assert "get_biggest_wins" in tool_names
        assert "get_dataset_summary" in tool_names
