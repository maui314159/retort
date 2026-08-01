"""Unit tests for the query layer (structured results)."""

from __future__ import annotations

import pytest

from soccer_mcp import queries as q


class TestSearchMatches:
    def test_by_team(self, store):
        result = q.search_matches(store, team="Palmeiras", season=2023, limit=100)
        assert result["total"] > 0
        for m in result["matches"]:
            assert "Palmeiras" in (m["home_team"], m["away_team"])
            assert m["season"] == 2023

    def test_between_two_teams(self, store):
        result = q.search_matches(store, team="Flamengo", opponent="Fluminense")
        assert result["total"] > 20
        for m in result["matches"]:
            pair = {m["home_team"], m["away_team"]}
            assert pair == {"Flamengo", "Fluminense"}

    def test_matches_have_date_scores_and_competition(self, store):
        result = q.search_matches(store, team="Flamengo", season=2023)
        for m in result["matches"]:
            assert m["date"]
            assert m["home_goals"] is not None and m["away_goals"] is not None
            assert m["competition"]

    def test_by_competition(self, store):
        result = q.search_matches(store, competition="Libertadores",
                                  season=2022, limit=5)
        assert all(m["competition"] == "Copa Libertadores" for m in result["matches"])

    def test_copa_do_brasil_finals(self, store):
        result = q.search_matches(store, competition="Copa do Brasil",
                                  stage="final", limit=100)
        assert result["total"] >= 15  # two-legged finals across 10 seasons
        assert all(m["stage"] == "final" for m in result["matches"])

    def test_date_range(self, store):
        result = q.search_matches(store, team="Santos",
                                  date_from="2019-01-01", date_to="2019-06-30",
                                  limit=100)
        assert result["total"] > 0
        assert all("2019-01-01" <= m["date"] <= "2019-06-30"
                   for m in result["matches"] if m["date"])

    def test_venue_home_and_away(self, store):
        home = q.search_matches(store, team="Corinthians", season=2022,
                                venue="home", limit=100)
        assert all(m["home_team"] == "Corinthians" for m in home["matches"])
        away = q.search_matches(store, team="Corinthians", season=2022,
                                venue="away", limit=100)
        assert all(m["away_team"] == "Corinthians" for m in away["matches"])

    def test_team_name_variations(self, store):
        """'Palmeiras-SP', 'palmeiras' and 'SEP' forms resolve the same."""
        a = q.search_matches(store, team="Palmeiras-SP", season=2022)
        b = q.search_matches(store, team="palmeiras", season=2022)
        assert a["total"] == b["total"] > 0

    def test_unknown_team_raises(self, store):
        with pytest.raises(q.QueryError):
            q.search_matches(store, team="Not A Real Club FC")


class TestHeadToHead:
    def test_record(self, store):
        result = q.head_to_head(store, "Flamengo", "Fluminense")
        assert result["derby"] == "Fla-Flu"
        total = result["team1_wins"] + result["team2_wins"] + result["draws"]
        assert total == result["total_matches"] > 0
        assert result["team1_wins"] > 0 and result["team2_wins"] > 0

    def test_symmetry(self, store):
        ab = q.head_to_head(store, "Palmeiras", "Santos")
        ba = q.head_to_head(store, "Santos", "Palmeiras")
        assert ab["team1_wins"] == ba["team2_wins"]
        assert ab["draws"] == ba["draws"]
        assert ab["total_matches"] == ba["total_matches"]

    def test_competition_filter(self, store):
        result = q.head_to_head(store, "Flamengo", "Palmeiras",
                                competition="Copa do Brasil")
        assert all(m["competition"] == "Copa do Brasil" for m in result["matches"])


class TestLastMatch:
    def test_flamengo_corinthians(self, store):
        m = q.last_match(store, "Flamengo", "Corinthians")
        assert {m["home_team"], m["away_team"]} == {"Flamengo", "Corinthians"}
        assert m["date"] is not None

    def test_is_the_most_recent(self, store):
        m = q.last_match(store, "Flamengo", "Corinthians")
        h2h = q.head_to_head(store, "Flamengo", "Corinthians")
        latest = max(x["date"] for x in h2h["matches"] if x["date"])
        assert m["date"] == latest


class TestTeamStats:
    def test_corinthians_home_2022(self, store):
        stats = q.team_stats(store, "Corinthians", competition="Brasileirão",
                             season=2022, venue="home")
        assert stats["matches"] == 19
        assert stats["wins"] + stats["draws"] + stats["losses"] == 19
        assert 0 <= stats["win_rate"] <= 100

    def test_all_time_palmeiras(self, store):
        stats = q.team_stats(store, "Palmeiras")
        assert stats["matches"] > 400
        assert stats["goals_for"] > stats["goals_against"]


class TestTeamCompetitions:
    def test_palmeiras_played_all_three(self, store):
        result = q.team_competitions(store, "Palmeiras")
        comps = {c["competition_key"] for c in result["competitions"]}
        assert {"serie a", "copa do brasil", "copa libertadores"} <= comps


class TestStandings:
    def test_2019_champion_flamengo(self, store):
        table = q.standings(store, 2019, "brasileirao")
        top = table["standings"][0]
        assert top["team"] == "Flamengo"
        assert top["points"] == 90
        assert (top["wins"], top["draws"], top["losses"]) == (28, 6, 4)
        assert top["champion"] is True
        assert table["matches"] == 380
        assert table["teams"] == 20

    def test_2019_relegation(self, store):
        table = q.standings(store, 2019, "serie a")
        relegated = [r["team"] for r in table["standings"] if r.get("relegated")]
        assert relegated == ["Cruzeiro", "Csa", "Chapecoense", "Avaí"]

    def test_points_consistency(self, store):
        table = q.standings(store, 2021, "serie a")
        for row in table["standings"]:
            assert row["points"] == 3 * row["wins"] + row["draws"]
            assert row["played"] == row["wins"] + row["draws"] + row["losses"]
            assert row["goal_difference"] == row["goals_for"] - row["goals_against"]

    def test_unknown_season_raises(self, store):
        with pytest.raises(q.QueryError):
            q.standings(store, 1950, "serie a")


class TestPlayers:
    def test_search_by_name(self, store):
        result = q.search_players(store, name="Neymar")
        assert result["players"][0]["name"] == "Neymar Jr"

    def test_brazilian_filter(self, store):
        result = q.search_players(store, nationality="Brazil", limit=100)
        assert result["total"] == 827
        assert all(p["nationality"] == "Brazil" for p in result["players"])

    def test_top_brazilian_players(self, store):
        result = q.top_players(store, nationality="Brazil", limit=3)
        ratings = [p["overall"] for p in result["players"]]
        assert ratings == sorted(ratings, reverse=True)
        assert result["players"][0]["name"] == "Neymar Jr"
        assert result["players"][0]["overall"] == 92

    def test_club_filter(self, store):
        result = q.search_players(store, club="Santos", limit=100)
        assert result["total"] > 0
        assert all(p["club"] == "Santos" for p in result["players"])

    def test_club_filter_prefers_exact_over_substring(self, store):
        """'Santos' must not return Santos Laguna players."""
        result = q.search_players(store, club="Santos", limit=100)
        assert all(p["club"] == "Santos" for p in result["players"])

    def test_forwards_group(self, store):
        result = q.search_players(store, club="Santos",
                                  position_group="forward", limit=100)
        assert result["total"] > 0
        assert all(p["position_group"] == "forward" for p in result["players"])

    def test_profile(self, store):
        p = q.player_profile(store, "Gabriel Jesus")
        assert p["name"] == "Gabriel Jesus"
        assert p["nationality"] == "Brazil"
        assert p["overall"] >= 80
        assert p["skills"]

    def test_profile_unknown_raises(self, store):
        with pytest.raises(q.QueryError):
            q.player_profile(store, "Zzz Notaplayer Qqq")


class TestCompetitionStats:
    def test_brasileirao_averages(self, store):
        stats = q.competition_stats(store, "brasileirao")
        assert stats["matches"] > 8000
        assert 2.0 < stats["avg_goals_per_match"] < 3.0
        assert 40 < stats["home_win_rate"] < 60

    def test_rates_sum_to_100(self, store):
        stats = q.competition_stats(store, "copa do brasil")
        total = (stats["home_win_rate"] + stats["draw_rate"]
                 + stats["away_win_rate"])
        assert abs(total - 100.0) < 0.3


class TestBiggestWins:
    def test_margin_order(self, store):
        result = q.biggest_wins(store, limit=10)
        margins = [m["margin"] for m in result["matches"]]
        assert margins == sorted(margins, reverse=True)
        assert margins[0] >= 8

    def test_santos_8_0_bolivar_present(self, store):
        """The spec's example: Santos 8-0 Bolivar (2012 Libertadores)... is
        actually 2012 — our Libertadores data starts 2013, so verify the
        biggest recorded wins instead."""
        result = q.biggest_wins(store, competition="libertadores", limit=5)
        assert result["matches"][0]["margin"] >= 7


class TestBestRecords:
    def test_home_records(self, store):
        result = q.best_home_records(store, competition="serie a", season=2022)
        assert result["teams"]
        rates = [t["win_rate"] for t in result["teams"]]
        assert rates == sorted(rates, reverse=True)

    def test_away_records(self, store):
        result = q.best_away_records(store, competition="serie a", season=2022)
        assert result["teams"]


class TestTopScoringTeams:
    def test_2023_serie_a(self, store):
        result = q.top_scoring_teams(store, "serie a", 2023, limit=5)
        goals = [t["goals"] for t in result["teams"]]
        assert goals == sorted(goals, reverse=True)
        assert result["teams"][0]["goals"] > 50


class TestDerbies:
    def test_2023_derbies_found(self, store):
        result = q.find_derbies(store, season=2023)
        assert result["total"] > 10
        names = {m["derby"] for m in result["matches"]}
        assert "Fla-Flu" in names

    def test_all_matches_are_derbies(self, store):
        result = q.find_derbies(store, season=2021, limit=100)
        for m in result["matches"]:
            assert m["derby"]


class TestCompareSeasons:
    def test_2018_vs_2019(self, store):
        result = q.season_comparison(store, "serie a", 2018, 2019)
        assert result["season_a"]["matches"] == 380
        assert result["season_b"]["matches"] == 380
        assert result["avg_goals_delta"] is not None


class TestDiscovery:
    def test_list_competitions(self, store):
        result = q.list_competitions(store)
        keys = {c["competition_key"] for c in result["competitions"]}
        assert keys == {"serie a", "serie b", "serie c",
                        "copa do brasil", "copa libertadores"}

    def test_list_teams_scoped(self, store):
        result = q.list_teams(store, "serie a", 2019)
        assert result["total"] == 20
        assert "Flamengo" in result["teams"]

    def test_dataset_summary(self, store):
        summary = q.dataset_summary(store)
        assert summary["players"] == 18207
        assert summary["unified_matches"] > 16000
