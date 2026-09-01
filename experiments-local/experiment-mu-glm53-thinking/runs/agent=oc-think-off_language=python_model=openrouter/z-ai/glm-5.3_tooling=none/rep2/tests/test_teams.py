"""BDD scenarios for team queries (Gherkin: get team statistics)."""

import soccer.queries as q


class TestTeamStats:
    def test_statistics_for_team_in_season(self, data):
        """Scenario: get team statistics.

        Given the match data is loaded
        When I request statistics for "Palmeiras" in season "2023"
        Then I should receive wins, losses, draws, and goals
        """
        s = q.team_stats(data, "Palmeiras", season=2023)
        assert s["matches"] > 30
        assert s["wins"] + s["draws"] + s["losses"] == s["matches"]
        assert s["goals_for"] > 0

    def test_home_record_for_season(self, data):
        """Scenario: what is Corinthians' home record in 2022?"""
        s = q.team_stats(data, "Corinthians", season=2022, venue="home")
        assert s["matches"] > 15
        assert s["away_record"] == {"w": 0, "d": 0, "l": 0}
        assert 0 <= s["win_rate"] <= 100

    def test_venue_home_only_counts_home_games(self, data):
        all_stats = q.team_stats(data, "Flamengo", season=2019)
        home = q.team_stats(data, "Flamengo", season=2019, venue="home")
        away = q.team_stats(data, "Flamengo", season=2019, venue="away")
        assert home["matches"] + away["matches"] == all_stats["matches"]

    def test_win_rate_consistent_with_home_away_splits(self, data):
        s = q.team_stats(data, "Grêmio", season=2019)
        assert (
            s["home_record"]["w"] + s["home_record"]["d"] + s["home_record"]["l"]
            + s["away_record"]["w"] + s["away_record"]["d"] + s["away_record"]["l"]
            == s["matches"]
        )

    def test_unknown_team_reports_error(self, data):
        assert "error" in q.team_stats(data, "NoSuch Team")

    def test_team_stats_across_competitions(self, data):
        s = q.team_stats(data, "Palmeiras", competition="Libertadores")
        assert s["matches"] > 0


class TestTeamCompetitions:
    def test_palmeiras_competitions(self, data):
        """Scenario: what competitions has Palmeiras played in?"""
        c = q.team_competitions(data, "Palmeiras")
        comps = c["competitions"]
        assert "Brasileirão Serie A" in comps
        assert "Copa Libertadores" in comps
        assert comps["Brasileirão Serie A"] > 100


class TestBestRecords:
    def test_best_home_record(self, data):
        """Scenario: which team has the best home record?"""
        r = q.best_record(data, "home", "Brasileirão")
        assert r["teams"]
        assert r["teams"][0]["win_rate"] >= r["teams"][-1]["win_rate"]

    def test_best_away_record(self, data):
        r = q.best_record(data, "away", "Brasileirão")
        assert r["teams"]
        for team in r["teams"]:
            assert team["matches"] >= 10
