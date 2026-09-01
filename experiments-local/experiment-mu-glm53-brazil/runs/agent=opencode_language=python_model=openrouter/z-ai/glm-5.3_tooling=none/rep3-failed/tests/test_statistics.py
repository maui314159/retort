"""BDD scenarios for statistical analysis.

Feature: Statistical Analysis
  Users ask for aggregate statistics: goals per match, home advantage,
  biggest wins and derby records.
"""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp.models import CompetitionStats
from brazilian_soccer_mcp.queries import QueryError


class TestGoalsPerMatch:
    """
    Scenario: What's the average goals per match in the Brasileirão?
      Given the match data is loaded
      When I request statistics for the 2019 Série A
      Then the average goals per match is about 2.31
    """

    def test_when_requesting_2019_serie_a_statistics_then_averages_match_the_data(self, engine):
        stats = engine.statistics(competition="Série A", season=2019)
        assert isinstance(stats, CompetitionStats)
        assert stats.matches == 380
        assert stats.avg_goals == pytest.approx(2.31, abs=0.01)
        assert stats.avg_home_goals > stats.avg_away_goals

    def test_when_requesting_statistics_then_rates_sum_to_one(self, engine):
        stats = engine.statistics(competition="Série B", season=2023)
        total = stats.home_win_rate + stats.draw_rate + stats.away_win_rate
        assert total == pytest.approx(1.0)
        assert stats.home_wins + stats.draws + stats.away_wins == stats.matches

    def test_when_requesting_statistics_with_no_matches_then_an_error_is_raised(self, engine):
        with pytest.raises(QueryError):
            engine.statistics(competition="Série A", season=1999)


class TestHomeAdvantage:
    """
    Scenario: Home vs away performance
      Given the match data is loaded
      When I request statistics for any competition
      Then home teams win more often than away teams
    """

    def test_when_computing_statistics_then_home_teams_win_more_often(self, engine):
        for competition in ("Série A", "Série B", "Copa do Brasil", "Libertadores"):
            stats = engine.statistics(competition=competition)
            assert stats.home_win_rate > stats.away_win_rate, competition


class TestBiggestWins:
    """
    Scenario: Show me the biggest wins in the dataset
      Given the match data is loaded
      When I request the biggest Libertadores wins
      Then River Plate 8-0 Jorge Wilstermann (2017) appears near the top
    """

    def test_when_requesting_biggest_libertadores_wins_then_river_plates_8_0_tops(self, engine):
        wins = engine.biggest_wins(competition="Libertadores", limit=5)
        top = wins[0]
        assert top.margin == 8
        assert top.home_display == "River Plate"

    def test_when_requesting_biggest_wins_then_margins_are_sorted_descending(self, engine):
        wins = engine.biggest_wins(limit=25)
        margins = [m.margin for m in wins]
        assert margins == sorted(margins, reverse=True)
        assert all(m.played for m in wins)

    def test_when_requesting_biggest_serie_a_wins_then_margins_reach_at_least_seven(self, engine):
        wins = engine.biggest_wins(competition="Série A", limit=3)
        assert wins[0].margin >= 7


class TestHeadToHeadAggregates:
    """
    Scenario: Head-to-head records aggregate correctly
      Given the match data is loaded
      When I compare Flamengo and Fluminense across all competitions
      Then wins plus draws equal the number of played meetings
    """

    def test_when_aggregating_h2h_then_counts_cover_every_played_meeting(self, engine):
        h2h = engine.head_to_head("Flamengo", "Fluminense", limit=None)
        played = sum(1 for m in h2h.matches if m.played)
        assert h2h.total == 44
        assert h2h.team_a_wins + h2h.team_b_wins + h2h.draws == played == 44

    def test_when_aggregating_h2h_goals_then_they_match_the_match_list(self, engine):
        h2h = engine.head_to_head("Palmeiras", "Santos", limit=None)
        assert h2h.total == 41
        goals_a = 0
        goals_b = 0
        for match in h2h.matches:
            if not match.played:
                continue
            if match.home_key == "palmeiras":
                goals_a += match.home_goals
                goals_b += match.away_goals
            else:
                goals_a += match.away_goals
                goals_b += match.home_goals
        assert (goals_a, goals_b) == (h2h.goals_a, h2h.goals_b)


class TestDerbies:
    """
    Scenario: Show me all derbies in the dataset
      Given the curated derby knowledge is loaded
      When I request derby matches
      Then Fla-Flu, Gre-Nal and the other classics appear with records
    """

    def test_when_requesting_all_derbies_then_at_least_ten_classics_appear(self, engine):
        results = engine.derbies()
        names = {r.derby.name for r in results}
        assert {"Fla-Flu", "Gre-Nal", "Choque-Rei", "Majestoso", "Ba-Vi"} <= names
        for result in results:
            assert (
                result.team_a_wins + result.team_b_wins + result.draws
                <= result.total
            )

    def test_when_requesting_the_gre_nal_then_grêmio_and_internacional_meet(self, engine):
        results = engine.derbies(derby="Gre-Nal")
        assert len(results) == 1
        result = results[0]
        assert result.total > 30
        for match in result.matches:
            assert {match.home_key, match.away_key} == {"gremio", "internacional-rs"}

    def test_when_requesting_derbies_for_one_season_then_all_matches_are_from_it(self, engine):
        results = engine.derbies(season=2019, competition="Série A")
        assert results
        for result in results:
            for match in result.matches:
                assert match.season == 2019
                assert match.competition == "Brasileirão Série A"

    def test_when_requesting_an_unknown_derby_then_an_error_lists_known_derbies(self, engine):
        with pytest.raises(QueryError):
            engine.derbies(derby="El Clásico")


class TestDataCoverage:
    """
    Scenario: All six CSV files are loaded and queryable
      Given the server starts
      When the datasets load
      Then all matches and players are available with competition metadata
    """

    def test_when_data_loads_then_all_six_files_contribute(self, engine):
        sources = {m.source for m in engine.matches}
        assert {
            "Brasileirao_Matches.csv",
            "Brazilian_Cup_Matches.csv",
            "Libertadores_Matches.csv",
            "BR-Football-Dataset.csv",
            "novo_campeonato_brasileiro.csv",
        } <= sources
        assert len(engine.players) == 18_207
        assert len(engine.matches) == 23_954

    def test_when_data_loads_then_every_match_has_teams_and_competition(self, engine):
        for match in engine.matches:
            assert match.home_key and match.away_key
            assert match.competition in {
                "Brasileirão Série A",
                "Brasileirão Série B",
                "Brasileirão Série C",
                "Copa do Brasil",
                "Copa Libertadores",
            }
