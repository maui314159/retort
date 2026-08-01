"""Functional tests for the query engine (spec capabilities 1-5)."""

from __future__ import annotations

import time

import pytest

from brazilian_soccer_mcp.queries import resolve_competition


class TestCompetitionResolution:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("Brasileirão Série A", "Brasileirão Série A"),
            ("brasileirao", "Brasileirão Série A"),
            ("Serie A", "Brasileirão Série A"),
            ("Campeonato Brasileiro", "Brasileirão Série A"),
            ("Copa do Brasil", "Copa do Brasil"),
            ("brazilian cup", "Copa do Brasil"),
            ("Libertadores", "Copa Libertadores"),
            ("copa libertadores", "Copa Libertadores"),
            (None, None),
        ],
    )
    def test_aliases(self, text, expected):
        assert resolve_competition(text) == expected


class TestMatchQueries:
    def test_fla_flu_matches(self, engine):
        result = engine.find_matches(team="Flamengo", versus="Fluminense")
        assert result["total"] >= 30
        for m in result["matches"]:
            pair = {m["home_team"], m["away_team"]}
            assert any("Flamengo" in t for t in pair)
            assert any("Fluminense" in t for t in pair)
            assert m["date"] and m["competition"]
            assert isinstance(m["home_goals"], int)
            assert isinstance(m["away_goals"], int)

    def test_team_season_filter(self, engine):
        result = engine.find_matches(team="Palmeiras", season=2022)
        assert result["total"] > 0
        for m in result["matches"]:
            assert m["season"] == 2022

    def test_competition_filter(self, engine):
        result = engine.find_matches(competition="Copa do Brasil", season=2023, limit=100)
        assert result["total"] > 0
        assert all(m["competition"] == "Copa do Brasil" for m in result["matches"])

    def test_date_range_filter(self, engine):
        result = engine.find_matches(date_from="2023-09-01", date_to="2023-09-30", limit=200)
        assert result["total"] > 0
        assert all(m["date"].startswith("2023-09") for m in result["matches"])

    def test_brazilian_date_format(self, engine):
        result = engine.find_matches(date_from="01/09/2023", date_to="30/09/2023", limit=200)
        assert result["total"] > 0
        assert all(m["date"].startswith("2023-09") for m in result["matches"])

    def test_unknown_team(self, engine):
        result = engine.find_matches(team="Wakanda United")
        assert "error" in result

    def test_name_variations_find_same_team(self, engine):
        """'Palmeiras-SP', 'palmeiras' and 'Palmeiras' are the same team."""
        a = engine.find_matches(team="Palmeiras-SP")
        b = engine.find_matches(team="palmeiras")
        c = engine.find_matches(team="Palmeiras")
        assert a["total"] == b["total"] == c["total"] > 0

    def test_full_name_variation(self, engine):
        a = engine.find_matches(team="Sport Club Corinthians Paulista")
        b = engine.find_matches(team="Corinthians-SP")
        assert a["total"] == b["total"] > 0

    def test_copa_do_brasil_finals(self, engine):
        """Libertadores finals are discoverable by stage."""
        result = engine.competition_schedule("Copa Libertadores", stage="final")
        assert result["total"] >= 10
        assert all(m["round"] == "final" for m in result["matches"])


class TestTeamQueries:
    def test_head_to_head_counts(self, engine):
        h2h = engine.head_to_head("Flamengo", "Fluminense")
        total = h2h["total_matches"]
        assert total == h2h["team1_wins"] + h2h["team2_wins"] + h2h["draws"]
        assert total >= 30
        assert h2h["last_match"] is not None

    def test_last_match_is_most_recent(self, engine):
        h2h = engine.head_to_head("Flamengo", "Corinthians")
        dates = [m["date"] for m in h2h["matches"]]
        assert dates == sorted(dates, reverse=True)
        assert h2h["last_match"]["date"] == dates[0]

    def test_team_record_shape(self, engine):
        rec = engine.team_record("Palmeiras", season=2022)
        assert rec["matches"] == rec["wins"] + rec["draws"] + rec["losses"]
        assert rec["matches"] > 0
        assert 0 <= rec["win_rate_pct"] <= 100
        assert rec["goals_for"] >= 0 and rec["goals_against"] >= 0

    def test_home_away_split(self, engine):
        rec = engine.team_record("Corinthians", season=2022)
        home = engine.team_record("Corinthians", season=2022, venue="home")
        away = engine.team_record("Corinthians", season=2022, venue="away")
        assert home["matches"] + away["matches"] == rec["matches"]
        assert home["wins"] + away["wins"] == rec["wins"]
        assert home["goals_for"] + away["goals_for"] == rec["goals_for"]

    def test_home_record_2022_serie_a(self, engine):
        """Every Série A club plays exactly 19 home games in 2022."""
        rec = engine.team_record("Corinthians", season=2022, competition="Serie A", venue="home")
        assert rec["matches"] == 19

    def test_team_competitions(self, engine):
        result = engine.team_competitions("Palmeiras")
        comps = {c["competition"] for c in result["competitions"]}
        assert "Brasileirão Série A" in comps
        assert "Copa do Brasil" in comps
        assert "Copa Libertadores" in comps

    def test_accent_insensitive_team_search(self, engine):
        a = engine.team_record("Grêmio", season=2022)
        b = engine.team_record("Gremio", season=2022)
        assert a["matches"] == b["matches"] > 0


class TestPlayerQueries:
    def test_search_brazilian_players(self, engine):
        result = engine.search_players(nationality="Brazil", limit=10)
        assert result["total"] > 800
        assert all(p["nationality"] == "Brazil" for p in result["players"])
        # Sorted by overall descending: Neymar (92) leads the dataset.
        assert result["players"][0]["name"] == "Neymar Jr"
        assert result["players"][0]["overall"] == 92

    def test_search_by_name(self, engine):
        result = engine.search_players(name="Neymar")
        assert result["total"] >= 1
        assert any("Neymar" in p["name"] for p in result["players"])

    def test_search_by_club(self, engine):
        result = engine.search_players(club="Grêmio")
        assert result["total"] == 20
        assert all(p["club"] == "Grêmio" for p in result["players"])

    def test_search_forwards(self, engine):
        result = engine.search_players(club="Santos", position_group="forward")
        assert result["total"] > 0
        assert all(p["position_group"] == "forward" for p in result["players"])

    def test_min_overall(self, engine):
        result = engine.search_players(nationality="Brazil", min_overall=85, limit=50)
        assert result["total"] > 0
        assert all(p["overall"] >= 85 for p in result["players"])

    def test_player_profile(self, engine):
        profile = engine.player_profile("Neymar")
        assert profile["name"] == "Neymar Jr"
        assert profile["overall"] == 92
        assert profile["club"] == "Paris Saint-Germain"
        assert "skills" in profile

    def test_player_profile_unknown(self, engine):
        assert "error" in engine.player_profile("Zzyzzy Unknown")

    def test_club_roster(self, engine):
        result = engine.club_roster("Fluminense")
        assert result["total"] == 20
        assert result["average_overall"] > 60

    def test_club_roster_accent_insensitive(self, engine):
        a = engine.club_roster("Grêmio")
        b = engine.club_roster("Gremio")
        assert a["total"] == b["total"] == 20


class TestCompetitionQueries:
    def test_2019_standings_match_history(self, engine):
        st = engine.standings(2019, "Brasileirão Série A")
        assert st["matches"] == 380
        assert st["champion"] == "Flamengo"
        top = st["standings"][0]
        assert (top["points"], top["wins"], top["draws"], top["losses"]) == (90, 28, 6, 4)
        # Spec example rows 2 and 3.
        assert st["standings"][1]["team"] == "Santos"
        assert st["standings"][1]["points"] == 74
        assert st["standings"][2]["team"] == "Palmeiras"
        assert st["standings"][2]["points"] == 74

    def test_points_consistency(self, engine):
        st = engine.standings(2019)
        for row in st["standings"]:
            assert row["points"] == 3 * row["wins"] + row["draws"]
            assert row["played"] == row["wins"] + row["draws"] + row["losses"]
            assert row["goal_difference"] == row["goals_for"] - row["goals_against"]
            assert row["played"] == 38
        assert [r["position"] for r in st["standings"]] == list(range(1, 21))

    def test_relegated_bottom_four(self, engine):
        st = engine.standings(2019)
        relegated_teams = {r["team"] for r in st["standings"][-4:]}
        assert set(st["relegated"]) == relegated_teams

    def test_libertadores_bracket_stages(self, engine):
        result = engine.competition_schedule("Copa Libertadores", season=2018)
        assert result["total"] > 0
        assert "final" in result["stages"]
        assert "group stage" in result["stages"]

    def test_unknown_season(self, engine):
        result = engine.standings(1950)
        assert "error" in result


class TestStatisticalAnalysis:
    def test_biggest_wins_sorted_by_margin(self, engine):
        result = engine.biggest_wins(limit=10)
        wins = result["biggest_wins"]
        margins = [abs(m["home_goals"] - m["away_goals"]) for m in wins]
        assert margins == sorted(margins, reverse=True)
        assert margins[0] >= 8

    def test_competition_stats(self, engine):
        stats = engine.competition_stats(competition="Brasileirão Série A")
        assert stats["matches"] > 8000
        assert 2.0 < stats["avg_goals_per_match"] < 3.5
        total = stats["home_wins"] + stats["draws"] + stats["away_wins"]
        assert total == stats["matches"]
        # Home advantage exists in Brazilian football.
        assert stats["home_win_rate_pct"] > stats["away_win_rate_pct"]

    def test_compare_seasons(self, engine):
        result = engine.compare_seasons(2018, 2019, competition="Brasileirão Série A")
        assert result["season_a"]["matches"] == 380
        assert result["season_b"]["matches"] == 380
        assert result["season_a"]["avg_goals_per_match"] > 0

    def test_top_scoring_teams(self, engine):
        result = engine.top_scoring_teams(season=2019, competition="Serie A")
        top = result["top_scoring_teams"]
        assert len(top) == 10
        goals = [t["goals"] for t in top]
        assert goals == sorted(goals, reverse=True)
        assert top[0]["team"] == "Flamengo"  # 86 goals in 2019


class TestPerformance:
    def test_simple_lookup_under_2s(self, engine):
        start = time.perf_counter()
        engine.find_matches(team="Flamengo", versus="Fluminense")
        engine.head_to_head("Palmeiras", "Santos")
        engine.player_profile("Neymar")
        assert time.perf_counter() - start < 2.0

    def test_aggregate_query_under_5s(self, engine):
        start = time.perf_counter()
        engine.standings(2019)
        engine.competition_stats()
        engine.biggest_wins(limit=50)
        assert time.perf_counter() - start < 5.0
