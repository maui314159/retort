"""BDD scenarios for competition queries.

Feature: Competition Queries
  Users ask about competitions: standings by season (calculated from
  match results), schedules, finals and champions.
"""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp.queries import QueryError, StandingsResult


class TestStandings2019:
    """
    Scenario: Who won the 2019 Brasileirão?
      Given the match data is loaded
      When I request the 2019 Série A standings
      Then Flamengo is champion with 90 points (28W, 6D, 4L)
      And Santos is second and Palmeiras third
    """

    def test_when_requesting_2019_standings_then_flamengo_is_champion(self, engine):
        result = engine.standings(2019)
        assert isinstance(result, StandingsResult)
        assert result.complete
        assert result.champion == "Flamengo"
        flamengo = result.rows[0]
        assert flamengo.points == 90
        assert (flamengo.wins, flamengo.draws, flamengo.losses) == (28, 6, 4)

    def test_when_requesting_2019_standings_then_the_top_three_match_history(self, engine):
        result = engine.standings(2019)
        top3 = [(row.position, row.team_display, row.points) for row in result.rows[:3]]
        assert top3 == [
            (1, "Flamengo", 90),
            (2, "Santos", 74),
            (3, "Palmeiras", 74),
        ]
        palmeiras = result.rows[2]
        assert (palmeiras.wins, palmeiras.draws, palmeiras.losses) == (21, 11, 6)

    def test_when_requesting_2019_standings_then_twenty_teams_played_380_matches(self, engine):
        result = engine.standings(2019)
        assert len(result.rows) == 20
        assert result.played == 380
        assert sum(row.matches for row in result.rows) == 760

    def test_when_requesting_2019_standings_then_the_four_relegated_teams_are_listed(self, engine):
        result = engine.standings(2019)
        assert set(result.relegated) == {"Cruzeiro", "CSA", "Chapecoense", "Avai"}


class TestStandingsAcrossEras:
    """
    Scenario: Standings work across every data source and era
      Given matches from 2003 to 2023
      When I request standings for 2003, 2016, 2022 and 2023
      Then each season produces a complete or flagged-incomplete table
    """

    def test_when_requesting_2003_standings_then_cruzeiro_is_champion(self, engine):
        result = engine.standings(2003)
        assert result.complete
        assert result.champion == "Cruzeiro"
        assert len(result.rows) == 24
        assert result.played == 552

    def test_when_requesting_2016_standings_then_palmeiras_is_champion(self, engine):
        result = engine.standings(2016)
        assert result.champion == "Palmeiras"
        assert result.rows[0].points == 80

    def test_when_requesting_2022_standings_then_palmeiras_leads_an_incomplete_season(self, engine):
        result = engine.standings(2022)
        assert result.rows[0].team_display == "Palmeiras"
        assert result.rows[0].points == 81
        assert not result.complete
        assert result.note and "incomplete" in result.note.lower()

    def test_when_requesting_2023_standings_then_the_season_is_flagged_incomplete(self, engine):
        result = engine.standings(2023)
        assert not result.complete
        assert result.champion is None
        assert result.rows[0].team_display == "Grêmio"


class TestStandingsOtherDivisions:
    """
    Scenario: Standings for Série B
      Given the Série B data is loaded
      When I request the 2023 Série B standings
      Then a complete table of twenty teams is calculated
    """

    def test_when_requesting_serie_b_2023_then_a_complete_table_is_calculated(self, engine):
        result = engine.standings(2023, competition="Série B")
        assert len(result.rows) == 20
        assert result.played == 380
        assert result.complete
        assert result.champion

    def test_when_requesting_standings_for_the_libertadores_then_an_error_is_raised(self, engine):
        with pytest.raises(QueryError):
            engine.standings(2019, competition="Libertadores")


class TestCompetitionOverview:
    """
    Scenario: What competitions are in the dataset?
      Given all six files are loaded
      When I list the competitions
      Then five competitions appear with their seasons and sources
    """

    def test_when_listing_competitions_then_all_five_appear(self, engine):
        overviews = engine.competition_overview()
        names = {o["competition"] for o in overviews}
        assert names == {
            "Brasileirão Série A",
            "Brasileirão Série B",
            "Brasileirão Série C",
            "Copa do Brasil",
            "Copa Libertadores",
        }

    def test_when_listing_serie_a_then_seasons_span_2003_to_2023(self, engine):
        overviews = engine.competition_overview("Série A")
        assert len(overviews) == 1
        seasons = overviews[0]["seasons"]
        assert seasons[0] == 2003
        assert seasons[-1] == 2023
        assert len(overviews[0]["sources"]) == 3

    def test_when_an_unknown_competition_is_requested_then_an_error_is_raised(self, engine):
        with pytest.raises(QueryError):
            engine.competition_overview("Premier League")


class TestCupQueries:
    """
    Scenario: Find all Copa do Brasil finals
      Given the cup data is loaded
      When I search for finals in the Copa do Brasil
      Then two-legged finals from 2012 to 2020 are returned
    """

    def test_when_searching_cup_finals_then_each_season_contributes_two_legs(self, engine):
        result = engine.search_matches(competition="Copa do Brasil", stage="final", limit=100)
        by_season = {}
        for match in result.matches:
            by_season.setdefault(match.season, []).append(match)
        assert len(by_season) == 9
        assert all(len(legs) == 2 for legs in by_season.values())
        assert 2020 in by_season

    def test_when_searching_the_2020_cup_final_then_palmeiras_beats_gremio(self, engine):
        result = engine.search_matches(
            competition="Copa do Brasil", season=2020, stage="final"
        )
        assert len(result.matches) == 2
        goals = {}
        for match in result.matches:
            goals[match.home_key] = match.home_goals
            goals[match.away_key] = match.away_goals
        assert goals.get("palmeiras", 0) > goals.get("gremio", 0)
