"""Unit tests for the query engine (match/team/player/competition/stats)."""

from __future__ import annotations

import time

import pytest

from brazilian_soccer_mcp import queries as q
from brazilian_soccer_mcp.data import BRASILEIRAO_A


class TestResolveTeam:
    def test_variant_names_resolve_to_same_key(self, kb):
        assert q.resolve_team(kb, "Palmeiras-SP")[0] == q.resolve_team(kb, "palmeiras")[0]

    def test_display_name_is_canonical(self, kb):
        _, display = q.resolve_team(kb, "Sao Paulo")
        assert display == "São Paulo"

    def test_unknown_team_raises_with_suggestions(self, kb):
        with pytest.raises(q.TeamNotFoundError) as exc:
            q.resolve_team(kb, "Flamengooo")
        assert "Flamengo" in exc.value.suggestions


class TestFindMatches:
    def test_by_team(self, kb):
        result = q.find_matches(kb, team="Flamengo")
        assert result["total"] > 500
        assert all(
            "Flamengo" in (m["home_team"], m["away_team"]) for m in result["matches"]
        )

    def test_by_team_and_opponent(self, kb):
        result = q.find_matches(kb, team="Flamengo", opponent="Fluminense")
        assert result["total"] > 20
        for match in result["matches"]:
            pair = {match["home_team"], match["away_team"]}
            assert pair == {"Flamengo", "Fluminense"}

    def test_by_season(self, kb):
        result = q.find_matches(kb, team="Palmeiras", season=2022, limit=100)
        assert result["total"] > 0
        assert all(m["season"] == 2022 for m in result["matches"])

    def test_by_competition(self, kb):
        result = q.find_matches(kb, team="Grêmio", competition="Libertadores", limit=100)
        assert result["total"] > 0
        assert all(m["competition"] == "Copa Libertadores" for m in result["matches"])

    def test_by_date_range(self, kb):
        result = q.find_matches(
            kb, team="Corinthians", date_from="2022-01-01", date_to="2022-12-31", limit=100
        )
        assert result["total"] > 0
        assert all(m["date"].startswith("2022") for m in result["matches"])

    def test_by_stage(self, kb):
        result = q.find_matches(kb, competition="Copa Libertadores", stage="Final", limit=100)
        assert result["total"] > 0
        assert all("Final" in m["stage"] for m in result["matches"])

    def test_stage_and_team(self, kb):
        result = q.find_matches(kb, team="Flamengo", competition="Copa Libertadores",
                                stage="Final", limit=100)
        assert result["total"] >= 1  # the 2019 title is in the dataset
        assert all("Flamengo" in (m["home_team"], m["away_team"])
                   for m in result["matches"])
        assert any(m["season"] == 2019 for m in result["matches"])

    def test_matches_sorted_most_recent_first(self, kb):
        result = q.find_matches(kb, team="Santos")
        dates = [m["date"] for m in result["matches"]]
        assert dates == sorted(dates, reverse=True)

    def test_match_fields_complete(self, kb):
        (match,) = q.find_matches(kb, team="Flamengo", limit=1)["matches"]
        assert set(match) == {
            "date", "home_team", "away_team", "home_goals", "away_goals",
            "competition", "season", "stage",
        }


class TestHeadToHead:
    def test_fla_flu(self, kb):
        result = q.head_to_head("Flamengo", "Fluminense", kb)
        assert result["total"] > 40
        assert result["wins_a"] + result["wins_b"] + result["draws"] == result["total"]
        assert result["goals_a"] > 0 and result["goals_b"] > 0

    def test_symmetry(self, kb):
        ab = q.head_to_head("Palmeiras", "Santos", kb)
        ba = q.head_to_head("Santos", "Palmeiras", kb)
        assert ab["total"] == ba["total"]
        assert ab["wins_a"] == ba["wins_b"]

    def test_competition_filter(self, kb):
        result = q.head_to_head("Flamengo", "Palmeiras", kb, competition="Copa do Brasil")
        assert all(m["competition"] == "Copa do Brasil" for m in result["matches"])


class TestTeamStats:
    def test_corinthians_home_2022(self, kb):
        result = q.team_stats("Corinthians", kb, season=2022, venue="home",
                              competition=BRASILEIRAO_A)
        assert result["matches"] == 19
        assert result["wins"] + result["draws"] + result["losses"] == 19
        assert result["wins"] == 12
        assert result["goals_for"] == 24
        assert result["goals_against"] == 11
        assert result["win_rate"] == pytest.approx(63.2, abs=0.1)

    def test_home_plus_away_equals_all(self, kb):
        home = q.team_stats("Flamengo", kb, season=2019, competition=BRASILEIRAO_A,
                            venue="home")
        away = q.team_stats("Flamengo", kb, season=2019, competition=BRASILEIRAO_A,
                            venue="away")
        total = q.team_stats("Flamengo", kb, season=2019, competition=BRASILEIRAO_A)
        assert home["matches"] + away["matches"] == total["matches"] == 38
        assert total["wins"] == 28  # historic 2019 campaign

    def test_competition_breakdown(self, kb):
        result = q.team_stats("Palmeiras", kb, season=2022)
        assert set(result["by_competition"]) >= {BRASILEIRAO_A}


class TestStandings:
    def test_2019_serie_a(self, kb):
        result = q.standings(2019, kb)
        table = result["table"]
        assert len(table) == 20
        champion = table[0]
        assert champion["team"] == "Flamengo"
        assert champion["points"] == 90
        assert champion["wins"] == 28
        assert champion["champion"] is True
        # Matches the historical table (and the spec's example).
        assert table[1]["team"] == "Santos" and table[1]["points"] == 74
        assert table[2]["team"] == "Palmeiras" and table[2]["points"] == 74

    def test_2019_relegation(self, kb):
        table = q.standings(2019, kb)["table"]
        relegated = {row["team"] for row in table if row["relegated"]}
        assert relegated == {"Cruzeiro", "CSA", "Chapecoense", "Avaí"}

    def test_points_consistency(self, kb):
        for row in q.standings(2018, kb)["table"]:
            assert row["points"] == 3 * row["wins"] + row["draws"]
            assert row["played"] == row["wins"] + row["draws"] + row["losses"]

    def test_unknown_season_gives_empty_table(self, kb):
        assert q.standings(1950, kb)["table"] == []


class TestSearchPlayers:
    def test_by_name(self, kb):
        result = q.search_players(kb, name="Neymar")
        assert result["total"] >= 1
        assert result["players"][0]["name"] == "Neymar Jr"
        assert result["players"][0]["overall"] == 92

    def test_brazilian_filter(self, kb):
        result = q.search_players(kb, nationality="Brazil", limit=5)
        assert result["total"] > 800
        assert all(p["nationality"] == "Brazil" for p in result["players"])

    def test_club_filter(self, kb):
        result = q.search_players(kb, club="Santos", limit=50)
        assert result["total"] > 0
        assert all("Santos" in p["club"] for p in result["players"])

    def test_position_filter(self, kb):
        result = q.search_players(kb, club="Grêmio", position="GK", limit=50)
        assert result["total"] > 0
        assert all(p["position"] == "GK" for p in result["players"])

    def test_position_group_forward(self, kb):
        result = q.search_players(kb, club="Santos", position_group="forward", limit=50)
        forwards = {"ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"}
        assert result["total"] > 0
        assert all(p["position"] in forwards for p in result["players"])

    def test_min_overall_and_sorting(self, kb):
        result = q.search_players(kb, nationality="Brazil", min_overall=88, limit=10)
        ratings = [p["overall"] for p in result["players"]]
        assert all(r >= 88 for r in ratings)
        assert ratings == sorted(ratings, reverse=True)
        assert result["players"][0]["name"] == "Neymar Jr"

    def test_limit_respected(self, kb):
        assert len(q.search_players(kb, nationality="Brazil", limit=3)["players"]) == 3

    def test_no_results(self, kb):
        assert q.search_players(kb, name="Zzz No Such Player")["total"] == 0


class TestClubSummary:
    def test_gremio_roster(self, kb):
        result = q.club_summary("Grêmio", kb)
        assert result["player_count"] == 20
        assert result["avg_overall"] > 65
        assert result["brazilian_count"] == 20
        assert result["players"][0]["overall"] >= result["players"][-1]["overall"]

    def test_unknown_club(self, kb):
        result = q.club_summary("No Such Club FC", kb)
        assert result["player_count"] == 0


class TestBiggestWins:
    def test_margins_descending(self, kb):
        result = q.biggest_wins(kb, limit=10)
        margins = [w["margin"] for w in result["biggest_wins"]]
        assert margins == sorted(margins, reverse=True)
        assert margins[0] >= 8

    def test_competition_filter(self, kb):
        result = q.biggest_wins(kb, competition=BRASILEIRAO_A, limit=5)
        assert all(w["competition"] == BRASILEIRAO_A for w in result["biggest_wins"])

    def test_score_matches_margin(self, kb):
        for win in q.biggest_wins(kb, limit=5)["biggest_wins"]:
            home, away = (int(x) for x in win["score"].split("-"))
            assert abs(home - away) == win["margin"]


class TestCompetitionStats:
    def test_2019_serie_a(self, kb):
        result = q.competition_stats(kb, competition=BRASILEIRAO_A, season=2019)
        assert result["matches"] == 380
        assert 2.0 < result["avg_goals_per_match"] < 3.5
        total = result["home_wins"] + result["draws"] + result["away_wins"]
        assert total == 380

    def test_rates_roughly_sum_to_100(self, kb):
        result = q.competition_stats(kb, competition=BRASILEIRAO_A, season=2018)
        assert (
            result["home_win_rate"] + result["draw_rate"] + result["away_win_rate"]
        ) == pytest.approx(100.0, abs=0.3)

    def test_per_season_breakdown(self, kb):
        result = q.competition_stats(kb, competition="Copa do Brasil")
        seasons = {row["season"] for row in result["per_season"]}
        assert {2012, 2023} <= seasons


class TestListings:
    def test_competitions(self, kb):
        result = q.list_competitions(kb)
        names = {c["competition"] for c in result["competitions"]}
        assert BRASILEIRAO_A in names and "Copa Libertadores" in names
        assert all(c["matches"] > 0 for c in result["competitions"])

    def test_list_teams_filter(self, kb):
        result = q.list_teams(kb, filter="Flam")
        assert "Flamengo" in result["teams"]
        assert all("Flam" in name for name in result["teams"])
        assert result["total"] == len(result["teams"])

    def test_list_teams_all(self, kb):
        assert q.list_teams(kb)["total"] > 200

    def test_dataset_summary(self, kb):
        result = q.dataset_summary(kb)
        assert result["total_matches"] == len(kb.matches)
        assert result["total_players"] == len(kb.players)
        assert len(result["files"]) == 7  # 6 CSVs + dedupe entry


class TestPerformance:
    def test_simple_lookup_under_2s(self, kb):
        start = time.perf_counter()
        q.head_to_head("Flamengo", "Corinthians", kb)
        assert time.perf_counter() - start < 2.0

    def test_aggregate_query_under_5s(self, kb):
        start = time.perf_counter()
        q.standings(2019, kb)
        q.competition_stats(kb, competition=BRASILEIRAO_A)
        q.biggest_wins(kb)
        assert time.perf_counter() - start < 5.0
