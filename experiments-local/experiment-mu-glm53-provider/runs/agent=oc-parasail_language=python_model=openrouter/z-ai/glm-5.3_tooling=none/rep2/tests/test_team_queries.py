"""GWT tests for team queries: stats, profiles and record rankings."""

from __future__ import annotations


class TestTeamStats:
    def test_given_team_and_season_when_queried_then_record_sums_match_matches(self, engine):
        result = engine.team_stats(team="Santos", season=2019)
        record = result["record"]
        assert record["wins"] + record["draws"] + record["losses"] == record["matches"]
        assert record["matches"] > 30

    def test_given_venue_home_when_queried_then_home_fixtures_only(self, engine):
        # Given Fluminense's matches
        # When filtering to home venue in one Série A season
        result = engine.team_stats(
            team="Fluminense", season=2019, competition="Série A", venue="home"
        )
        # Then they hosted exactly 19 matches (20-team double round-robin)
        assert result["record"]["matches"] == 19

    def test_given_venue_away_when_queried_then_away_fixtures_only(self, engine):
        result = engine.team_stats(
            team="Fluminense", season=2019, competition="Série A", venue="away"
        )
        assert result["record"]["matches"] == 19

    def test_given_competition_filter_when_queried_then_smaller_scope(self, engine):
        everything = engine.team_stats(team="Flamengo")
        serie_a_only = engine.team_stats(team="Flamengo", competition="Série A")
        assert serie_a_only["record"]["matches"] < everything["record"]["matches"]

    def test_given_invalid_venue_when_queried_then_error(self, engine):
        assert "error" in engine.team_stats(team="Flamengo", venue="neutral")

    def test_given_spec_example_when_corinthians_2022_home_then_expected_record(self, engine):
        # Spec example: "What is Corinthians' home record in 2022?"
        result = engine.team_stats(
            team="Corinthians", season=2022, competition="Série A", venue="home"
        )
        record = result["record"]
        assert record["matches"] == 19
        assert (record["wins"], record["draws"], record["losses"]) == (12, 4, 3)
        assert "Win rate" in result["summary"]


class TestTeamProfile:
    def test_given_major_club_when_profiled_then_cross_competition_coverage(self, engine):
        profile = engine.team_profile("Palmeiras")
        competitions = [entry["competition"] for entry in profile["competitions"]]
        assert "Brasileirão Série A" in competitions
        assert "Copa do Brasil" in competitions
        assert "Copa Libertadores" in competitions
        assert profile["overall_record"]["matches"] > 500

    def test_given_fifa_covered_club_when_profiled_then_squad_listed(self, engine):
        profile = engine.team_profile("Grêmio")
        assert profile["squad"], "Grêmio is covered by the FIFA dataset"
        assert all(p["club"] == "Grêmio" for p in profile["squad"])

    def test_given_fifa_uncovered_club_when_profiled_then_squad_noted(self, engine):
        profile = engine.team_profile("Flamengo")
        assert profile["squad"] == []
        assert "does not cover" in profile["summary"]

    def test_given_profile_when_rendered_then_last_match_present(self, engine):
        profile = engine.team_profile("Santos")
        assert profile["last_match"] is not None
        assert "Most recent match" in profile["summary"]


class TestBestRecords:
    def test_given_home_records_when_ranked_then_leading_team_has_best_rate(self, engine):
        result = engine.best_records(venue="home", minimum_matches=100, limit=5)
        rates = [team["win_rate"] for team in result["ranking"]]
        assert rates == sorted(rates, reverse=True)
        assert all(team["matches"] >= 100 for team in result["ranking"])

    def test_given_away_records_when_ranked_then_minimum_respected(self, engine):
        result = engine.best_records(venue="away", minimum_matches=200, limit=10)
        assert result["ranking"]
        assert all(team["matches"] >= 200 for team in result["ranking"])

    def test_given_season_scope_when_ranked_then_smaller_pools(self, engine):
        result = engine.best_records(
            venue="all", competition="Série A", season=2019, minimum_matches=10
        )
        assert all(team["matches"] <= 38 for team in result["ranking"])
