"""Tests for aggregate statistics (R10) and derby search."""

from brazilian_soccer_mcp.queries import QueryEngine


class TestCompetitionStats:
    def test_avg_goals_matches_manual_computation(self, engine, dataset):
        with_goals = [
            m for m in dataset.matches
            if m.competition == "Brasileirão"
            and m.home_goals is not None and m.away_goals is not None
        ]
        expected = round(
            sum(m.home_goals + m.away_goals for m in with_goals) / len(with_goals), 2
        )
        result = engine.get_competition_stats(competition="Brasileirão")
        assert result["matches"] == len(with_goals)
        assert result["avg_goals_per_match"] == expected

    def test_rates_sum_to_hundred(self, engine):
        result = engine.get_competition_stats(competition="Brasileirão")
        total = (
            result["home_win_rate"] + result["away_win_rate"] + result["draw_rate"]
        )
        assert 99.5 < total < 100.5

    def test_all_competitions_stats(self, engine):
        result = engine.get_competition_stats()
        assert result["competition"] == "all"
        assert result["matches"] > 10_000
        assert 2.0 < result["avg_goals_per_match"] < 3.5
        assert 0 < result["home_win_rate"] < 100

    def test_top_scoring_teams(self, engine):
        result = engine.get_competition_stats(competition="Brasileirão", top=10)
        teams = result["top_scoring_teams"]
        assert len(teams) == 10
        goals = [t["goals"] for t in teams]
        assert goals == sorted(goals, reverse=True)
        # goals counted must equal the competition total
        assert sum(goals) > 5_000

    def test_biggest_wins_ranked(self, engine):
        result = engine.get_competition_stats(competition="Brasileirão", top=5)
        biggest = result["biggest_wins"]
        assert 0 < len(biggest) <= 5
        # verify against the real maximum margin in the data
        margins = [
            abs(m.home_goals - m.away_goals)
            for m in dataset_margins(engine)
            if m.competition == "Brasileirão"
            and m.home_goals is not None and m.away_goals is not None
        ]
        assert max(margins) >= 4

    def test_season_scoped_stats(self, engine):
        result = engine.get_competition_stats(competition="Brasileirão", season=2019)
        assert result["season"] == 2019
        assert result["matches"] >= 380


def dataset_margins(engine: QueryEngine):
    return engine.dataset.matches


class TestBestRecords:
    def test_home_records_ranked(self, engine):
        result = engine.get_best_records(venue="home", season=2019, min_matches=10)
        rankings = result["rankings"]
        assert len(rankings) >= 5
        rates = [r["win_rate"] for r in rankings]
        assert rates == sorted(rates, reverse=True)
        assert all(r["played"] >= 10 for r in rankings)

    def test_best_home_team_is_champion_season(self, engine):
        result = engine.get_best_records(venue="home", season=2019, min_matches=10)
        assert result["rankings"][0]["team"] == "Flamengo"

    def test_away_records(self, engine):
        result = engine.get_best_records(venue="away", season=2023, min_matches=8)
        assert result["venue"] == "away"
        assert result["rankings"]
        assert all(r["played"] >= 8 for r in result["rankings"])

    def test_invalid_venue_errors(self, engine):
        result = engine.get_best_records(venue="middle")
        assert "error" in result

    def test_min_matches_filter(self, engine):
        result = engine.get_best_records(venue="home", min_matches=30)
        assert all(r["played"] >= 30 for r in result["rankings"])


class TestDerbySearch:
    def test_derbies_found(self, engine):
        result = engine.search_derbies(limit=50)
        assert result["total_matches"] > 100

    def test_derby_matches_are_rivalries(self, engine):
        from brazilian_soccer_mcp.normalize import derby_name

        result = engine.search_derbies(season=2023, limit=50)
        assert result["total_matches"] > 0
        for match in result["matches"]:
            assert match["derby"] == derby_name(match["home_team"], match["away_team"])
            assert match["derby"]

    def test_fla_flu_in_2023(self, engine):
        result = engine.search_derbies(season=2023, competition="Brasileirão", limit=50)
        fla_flu = [
            m for m in result["matches"]
            if {m["home_team"], m["away_team"]} == {"Flamengo", "Fluminense"}
        ]
        assert fla_flu
        assert fla_flu[0]["derby"] == "Fla-Flu"

    def test_derby_competition_filter(self, engine):
        result = engine.search_derbies(competition="Libertadores", limit=50)
        assert all(m["competition"] == "Libertadores" for m in result["matches"])


class TestDiscovery:
    def test_list_teams(self, engine):
        result = engine.list_teams(limit=5)
        assert result["team_count"] > 100
        assert len(result["teams"]) == 5
        counts = [t["matches"] for t in result["teams"]]
        assert counts == sorted(counts, reverse=True)

    def test_list_teams_competition_scoped(self, engine):
        result = engine.list_teams(competition="Libertadores", limit=10)
        assert result["competition"] == "Libertadores"
        assert result["teams"]

    def test_list_competitions(self, engine):
        result = engine.list_competitions()
        names = {c["competition"] for c in result["competitions"]}
        assert {"Brasileirão", "Copa do Brasil", "Libertadores"} <= names
        for entry in result["competitions"]:
            assert entry["season_range"]
