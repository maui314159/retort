"""Feature: Statistical Analysis

Background:
    Given the match data is loaded
    And statistics are computed from single canonical sources per season
"""

from __future__ import annotations

import pytest

from brazilian_soccer import query


class TestAverageGoals:
    """Scenario: Average goals per match
        Given the match data is loaded
        When I compute average goals for a competition
        Then the average and outcome rates should be returned
    """

    def test_given_serie_a_when_computing_average_goals_then_plausible_values(self, dataset):
        result = query.average_goals(dataset, competition="Serie A")
        assert result["matches"] > 5000
        assert 2.0 < result["avg_goals"] < 3.0
        assert 40 < result["home_win_rate"] < 60
        assert result["home_win_rate"] > result["away_win_rate"]

    def test_given_one_season_when_computing_average_goals_then_only_that_season(self, dataset):
        result = query.average_goals(dataset, competition="Serie A", season=2019)
        assert result["matches"] == 380
        assert 2.0 < result["avg_goals"] < 3.0

    def test_given_one_team_when_computing_average_goals_then_only_team_matches(self, dataset):
        result = query.average_goals(dataset, competition="Serie A", season=2019, team="Flamengo")
        assert result["matches"] == 38


class TestBiggestWins:
    """Scenario: Biggest wins in the dataset
        Given the match data is loaded
        When I rank matches by margin
        Then the largest victories should be returned in order
    """

    def test_given_all_data_when_ranking_biggest_wins_then_sorted_by_margin(self, dataset):
        result = query.biggest_wins(dataset, limit=5)
        margins = [w["margin"] for w in result["wins"]]
        assert margins == sorted(margins, reverse=True)
        assert margins[0] >= 7

    def test_given_libertadores_when_ranking_biggest_wins_then_river_plate_8_0_present(self, dataset):
        result = query.biggest_wins(dataset, competition="Libertadores", limit=3)
        top = result["wins"][0]
        assert top["home"] == "River Plate"
        assert (top["home_goals"], top["away_goals"]) == (8, 0)
        assert top["away"] == "Jorge Wilstermann"

    def test_given_one_team_when_ranking_biggest_wins_then_only_team_matches(self, dataset):
        result = query.biggest_wins(dataset, team="Palmeiras", limit=5)
        assert result["wins"]
        for win in result["wins"]:
            assert win["home"] == "Palmeiras" or win["away"] == "Palmeiras"


class TestHeadToHeadRecord:
    """Scenario: Compare teams head-to-head
        Given the match data is loaded
        When I request a head-to-head record
        Then wins, draws and total matches should be consistent
    """

    def test_given_flamengo_and_fluminense_when_comparing_then_record_consistent(self, dataset):
        result = query.head_to_head(dataset, "Flamengo", "Fluminense")
        assert result["total"] == result["wins_a"] + result["wins_b"] + result["draws"] + result["unscored"]
        assert result["total"] > 40

    def test_given_palmeiras_and_santos_when_comparing_then_matches_listed_with_context(self, dataset):
        result = query.head_to_head(dataset, "Palmeiras", "Santos", limit=5)
        for match in result["matches"]:
            assert match["competition"]
            assert match["date"]

    def test_given_head_to_head_with_competition_filter_then_only_that_competition(self, dataset):
        result = query.head_to_head(dataset, "Flamengo", "Fluminense", competition="Libertadores")
        for match in result["matches"]:
            assert match["competition"] == "Copa Libertadores"


class TestHomeVsAwayPerformance:
    """Scenario: Home vs away performance
        Given the match data is loaded
        When I compare outcome rates
        Then home teams should win more often than away teams
    """

    def test_given_multiple_competitions_when_computing_rates_then_home_advantage_everywhere(self, dataset):
        for competition in ("Serie A", "Serie B", "Copa do Brasil"):
            result = query.average_goals(dataset, competition=competition)
            assert result["home_win_rate"] > result["away_win_rate"], competition

    def test_given_best_away_teams_when_ranking_then_rates_below_home_leaders(self, dataset):
        away = query.best_records(dataset, competition="Serie A", venue="away", min_matches=100, limit=3)
        home = query.best_records(dataset, competition="Serie A", venue="home", min_matches=100, limit=3)
        assert home["records"][0]["win_rate"] > away["records"][0]["win_rate"]


class TestSeasonComparison:
    """Scenario: Compare the 2018 and 2019 seasons
        Given aggregated season statistics
        When I compare two seasons
        Then each summary should include goals, home advantage and champion
    """

    def test_given_2018_and_2019_when_comparing_then_both_summaries_complete(self, dataset):
        result = query.season_comparison(dataset, "Serie A", 2018, 2019)
        assert len(result["seasons"]) == 2
        by_season = {s["season"]: s for s in result["seasons"]}
        assert by_season[2018]["champion"] == "Palmeiras"
        assert by_season[2019]["champion"] == "Flamengo"
        for summary in result["seasons"]:
            assert summary["matches"] == 380
            assert 2.0 < summary["avg_goals"] < 3.0
            assert summary["home_win_rate"] > summary["away_win_rate"]
            assert summary["biggest_win"] is not None


class TestCrossFileQueries:
    """Scenario: Cross-file queries (player + match data)
        Given the FIFA data and the match files
        When I combine team statistics with player data
        Then both sources should contribute to the answer
    """

    def test_given_gremio_when_combining_record_and_squad_then_both_present(self, dataset):
        profile = query.team_profile(dataset, "Grêmio")
        assert profile["record"]["played"] > 500
        assert profile["players_at_club"] == 20

    def test_given_brazilian_clubs_in_fifa_when_checking_against_match_data_then_all_recognized(self, dataset):
        result = query.players_by_club(dataset)
        for club in result["clubs"]:
            assert club["club"] in {
                dataset.team_display(t) for t in dataset.brazilian_clubs
            }
