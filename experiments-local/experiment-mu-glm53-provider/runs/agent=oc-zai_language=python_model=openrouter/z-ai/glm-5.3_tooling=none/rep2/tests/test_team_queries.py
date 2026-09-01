"""Feature: Team Queries

Background:
    Given the match data is loaded
"""

from __future__ import annotations

import pytest

from brazilian_soccer import query
from brazilian_soccer.query import QueryError


class TestTeamHomeRecord:
    """Scenario: Get a team's home record for a season
        Given the match data is loaded
        When I request Corinthians' home record in the 2022 Brasileirão
        Then I should receive matches, wins, draws, losses and goals
    """

    def test_given_corinthians_2022_when_requesting_home_record_then_full_season(self, dataset):
        result = query.team_stats(
            dataset, "Corinthians", competition="Serie A", season=2022, venue="home",
        )
        assert result["played"] == 19
        assert result["wins"] == 12
        assert result["draws"] == 4
        assert result["losses"] == 3
        assert result["goals_for"] == 24
        assert result["goals_against"] == 11
        assert result["win_rate"] == pytest.approx(63.2, abs=0.1)

    def test_given_home_and_away_records_when_combined_then_match_overall(self, dataset):
        home = query.team_stats(dataset, "Corinthians", competition="Serie A", season=2022, venue="home")
        away = query.team_stats(dataset, "Corinthians", competition="Serie A", season=2022, venue="away")
        overall = query.team_stats(dataset, "Corinthians", competition="Serie A", season=2022)
        for field in ("played", "wins", "draws", "losses", "goals_for", "goals_against"):
            assert home[field] + away[field] == overall[field]


class TestTeamSeasonRecord:
    """Scenario: Get full team statistics for a season
        Given the match data is loaded
        When I request statistics for "Palmeiras" in season "2023"
        Then I should receive wins, losses, draws, and goals
    """

    def test_given_palmeiras_2023_when_requesting_stats_then_wdl_and_goals_present(self, dataset):
        result = query.team_stats(dataset, "Palmeiras", competition="Serie A", season=2023)
        assert result["played"] == 37
        assert result["wins"] + result["draws"] + result["losses"] == result["played"]
        assert result["goals_for"] > 0 and result["goals_against"] > 0
        assert result["points"] == result["wins"] * 3 + result["draws"]

    def test_given_a_season_where_two_sources_overlap_when_computing_stats_then_no_double_counting(self, dataset):
        result = query.team_stats(dataset, "Flamengo", competition="Serie A", season=2019)
        assert result["played"] == 38


class TestTeamGoalsScored:
    """Scenario: Which team scored the most goals in Serie A 2023?
        Given standings computed from match results
        When I look for the top-scoring team
        Then the answer should be derivable from the table
    """

    def test_given_serie_a_2023_when_ranking_by_goals_then_top_team_found(self, dataset):
        table, _ = dataset.league_table("Serie A", 2023)
        ranking = sorted(table, key=lambda r: -r.goals_for)
        assert ranking[0].goals_for >= ranking[1].goals_for
        assert ranking[0].played in (37, 38)

    def test_given_serie_a_2019_when_ranking_by_goals_then_flamengo_top(self, dataset):
        table, _ = dataset.league_table("Serie A", 2019)
        ranking = sorted(table, key=lambda r: -r.goals_for)
        assert dataset.team_display(ranking[0].team) == "Flamengo"


class TestTeamCompetitions:
    """Scenario: What competitions has Palmeiras played in?
        Given all match files
        When I ask for a team's competitions
        Then every competition containing that team should be listed
    """

    def test_given_palmeiras_when_asking_competitions_then_serie_a_copa_and_libertadores(self, dataset):
        result = query.team_competitions(dataset, "Palmeiras")
        competitions = {c["competition"] for c in result["competitions"]}
        assert "Brasileirão Série A" in competitions
        assert "Copa do Brasil" in competitions
        assert "Copa Libertadores" in competitions
        serie_a = next(c for c in result["competitions"] if c["competition"] == "Brasileirão Série A")
        assert serie_a["first_season"] <= 2015
        assert serie_a["last_season"] == 2023

    def test_given_a_libertadores_only_foreign_club_when_asking_then_only_libertadores(self, dataset):
        result = query.team_competitions(dataset, "Boca Juniors")
        competitions = {c["competition"] for c in result["competitions"]}
        assert competitions == {"Copa Libertadores"}


class TestBestRecords:
    """Scenario: Which team has the best home/away record?
        Given the match data is loaded
        When I rank teams by win rate
        Then only teams with enough matches should qualify
    """

    def test_given_serie_a_2019_when_ranking_home_records_then_reasonable_result(self, dataset):
        result = query.best_records(
            dataset, competition="Serie A", season=2019, venue="home", min_matches=15,
        )
        assert len(result["records"]) >= 5
        rates = [r["win_rate"] for r in result["records"]]
        assert rates == sorted(rates, reverse=True)
        assert all(r["played"] >= 15 for r in result["records"])

    def test_given_serie_a_2023_when_ranking_away_records_then_flamengo_leads(self, dataset):
        result = query.best_records(
            dataset, competition="Serie A", season=2023, venue="away", min_matches=15, limit=3,
        )
        assert result["records"][0]["team"] == "Flamengo"


class TestTeamProfile:
    """Scenario: Combined team view across match and player files
        Given match data and the FIFA player database
        When I request a team profile
        Then I should get the record, competitions and players together
    """

    def test_given_gremio_when_profiling_then_record_and_players_combined(self, dataset):
        result = query.team_profile(dataset, "Grêmio")
        assert result["team"] == "Grêmio"
        assert result["record"]["played"] > 500
        assert any(c["competition"] == "Copa Libertadores" for c in result["competitions"])
        assert result["players_at_club"] == 20
        assert len(result["top_players"]) == 5

    def test_given_club_not_in_fifa_when_profiling_then_no_players_but_record_present(self, dataset):
        result = query.team_profile(dataset, "Palmeiras")
        assert result["record"]["played"] > 500
        assert result["players_at_club"] == 0
