"""BDD scenarios for statistical analysis queries."""

import soccer.queries as q


class TestGoalsStatistics:
    def test_average_goals_brasileirao(self, data):
        """Scenario: what's the average goals per match in the Brasileirão?"""
        g = q.goals_statistics(data, "Brasileirão Serie A")
        assert g["matches"] > 1000
        assert 1.5 < g["avg_goals_per_match"] < 3.5
        assert (
            g["home_wins"] + g["away_wins"] + g["draws"] == g["matches"]
        )
        assert g["home_win_rate"] > g["away_win_rate"]  # home advantage

    def test_home_advantage_across_all_data(self, data):
        g = q.goals_statistics(data)
        assert g["home_win_rate"] > g["away_win_rate"]

    def test_unknown_competition(self, data):
        assert "error" in q.goals_statistics(data, "English Premier League")


class TestBiggestWins:
    def test_biggest_wins_ordered_by_margin(self, data):
        """Scenario: show me the biggest wins in the dataset."""
        r = q.biggest_wins(data, limit=10)
        wins = r["biggest_wins"]
        assert len(wins) == 10
        margins = [w["margin"] for w in wins]
        assert margins == sorted(margins, reverse=True)
        assert margins[0] >= 6

    def test_biggest_wins_limited_to_competition(self, data):
        r = q.biggest_wins(data, competition="Libertadores", limit=5)
        for w in r["biggest_wins"]:
            assert w["competition"] == "Copa Libertadores"


class TestSeasonComparison:
    def test_compare_two_seasons(self, data):
        """Scenario: compare the 2018 and 2019 seasons."""
        r = q.season_comparison(data, 2018, 2019, "Brasileirão")
        assert r["stats_a"]["matches"] > 300
        assert r["stats_b"]["matches"] > 300
        for stats in (r["stats_a"], r["stats_b"]):
            assert 1.5 < stats["avg_goals_per_match"] < 3.5


class TestDerbies:
    def test_fla_flu_derby_exists(self, data):
        """Scenario: find Fla-Flu derby matches."""
        r = q.find_derbies(data)
        assert r["total"] > 30
        fla_flu = [
            m
            for m in r["matches"]
            if {m["home"], m["away"]} == {"flamengo", "fluminense"}
        ]
        assert fla_flu

    def test_derbies_in_a_season(self, data):
        r = q.find_derbies(data, season=2023)
        assert 0 < r["total"] < 100
        for m in r["matches"]:
            assert m["season"] == 2023


class TestDataCoverage:
    def test_all_datasets_loaded(self, data):
        """All six CSV files are loadable and queryable."""
        assert len(data.matches) > 15000
        assert len(data.players) == 18207
        comps = {m.competition for m in data.matches}
        assert {
            "Brasileirão Serie A",
            "Copa do Brasil",
            "Copa Libertadores",
            "Série B",
            "Série C",
        } <= comps
        assert data.matches[0].date <= data.matches[-1].date  # sorted

    def test_detailed_statistics_available(self, data):
        """Corner/shot statistics from BR-Football-Dataset survive loading."""
        with_stats = [m for m in data.matches if m.stats]
        assert len(with_stats) > 1000
        assert any("home_shots" in m.stats for m in with_stats)
