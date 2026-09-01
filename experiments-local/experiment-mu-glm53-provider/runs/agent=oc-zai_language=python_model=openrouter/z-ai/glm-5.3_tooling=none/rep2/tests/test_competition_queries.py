"""Feature: Competition Queries

Background:
    Given standings are calculated from match results
    And cup champions are determined from final-stage matches
"""

from __future__ import annotations

import pytest

from brazilian_soccer import query
from brazilian_soccer.query import QueryError


class TestLeagueStandings:
    """Scenario: Calculate standings by season
        Given the match data is loaded
        When I request the 2019 Brasileirão standings
        Then Flamengo should be champion with 90 points
        And every team should have consistent W/D/L and goal totals
    """

    def test_given_2019_serie_a_when_computing_standings_then_flamengo_champion(self, dataset):
        result = query.standings(dataset, "Serie A", 2019)
        top = result["table"][0]
        assert top["team"] == "Flamengo"
        assert top["points"] == 90
        assert (top["wins"], top["draws"], top["losses"]) == (28, 6, 4)
        assert top["champion"] is True

    def test_given_any_season_when_computing_standings_then_totals_are_consistent(self, dataset):
        result = query.standings(dataset, "Serie A", 2019)
        for row in result["table"]:
            assert row["wins"] + row["draws"] + row["losses"] == row["played"]
            assert row["points"] == row["wins"] * 3 + row["draws"]
            assert row["goal_diff"] == row["goals_for"] - row["goals_against"]
        assert result["scored_matches"] == 380

    def test_given_2015_season_when_computing_standings_then_corinthians_champion(self, dataset):
        result = query.standings(dataset, "Brasileirão", 2015)
        assert result["table"][0]["team"] == "Corinthians"
        assert result["table"][0]["points"] == 81

    def test_given_2003_historical_season_when_computing_standings_then_table_produced(self, dataset):
        result = query.standings(dataset, "Serie A", 2003)
        assert len(result["table"]) == 24
        assert all(row["played"] == 46 for row in result["table"])


class TestRelegation:
    """Scenario: Which teams were relegated?
        Given the standings with a relegation zone
        When I request the 2020 Serie A standings
        Then the bottom four should be marked as relegated
    """

    def test_given_2020_serie_a_when_computing_standings_then_relegation_zone_marked(self, dataset):
        result = query.standings(dataset, "Serie A", 2020)
        relegated = [row["team"] for row in result["table"] if row["relegated"]]
        assert set(relegated) == {"Coritiba", "Botafogo", "Vasco da Gama", "Goiás"}
        assert len(relegated) == 4

    def test_given_cup_competition_when_asking_standings_then_error_with_hint(self, dataset):
        with pytest.raises(QueryError, match="knockout"):
            query.standings(dataset, "Copa do Brasil", 2019)


class TestLeagueChampion:
    """Scenario: Who won the league?
        Given standings computed from matches
        When I ask for the champion
        Then the top team should be returned with its record
    """

    def test_given_2019_serie_a_when_asking_champion_then_flamengo(self, dataset):
        result = query.champion(dataset, "Brasileirão", 2019)
        assert result["champion"] == "Flamengo"
        assert result["method"] == "top of the points table"
        assert result["points"] == 90

    def test_given_2021_serie_a_when_asking_champion_then_atletico_mg(self, dataset):
        result = query.champion(dataset, "Serie A", 2021)
        assert result["champion"] == "Atlético-MG"
        assert result["points"] == 84

    def test_given_2022_serie_a_when_asking_champion_then_palmeiras(self, dataset):
        result = query.champion(dataset, "Serie A", 2022)
        assert result["champion"] == "Palmeiras"
        assert result["points"] == 81


class TestCupChampion:
    """Scenario: Determine cup champions from finals
        Given the cup final matches
        When I aggregate the final legs
        Then the champion should be the aggregate winner
        And ties on aggregate should be reported as penalty decisions
    """

    def test_given_libertadores_2019_when_asking_champion_then_flamengo(self, dataset):
        result = query.champion(dataset, "Libertadores", 2019)
        assert result["champion"] == "Flamengo"
        assert result["method"] == "aggregate score"

    def test_given_libertadores_2018_when_asking_champion_then_river_plate(self, dataset):
        result = query.champion(dataset, "Libertadores", 2018)
        assert result["champion"] == "River Plate"
        assert (result["goals_a"], result["goals_b"]) == (3, 5)

    def test_given_libertadores_2013_when_final_tied_on_aggregate_then_penalties_reported(self, dataset):
        result = query.champion(dataset, "Libertadores", 2013)
        assert result["champion"] is None
        assert "penalties" in result["method"]

    def test_given_copa_do_brasil_2020_when_asking_champion_then_palmeiras(self, dataset):
        result = query.champion(dataset, "Copa do Brasil", 2020)
        assert result["champion"] == "Palmeiras"

    def test_given_copa_do_brasil_2013_when_asking_champion_then_flamengo(self, dataset):
        result = query.champion(dataset, "Copa do Brasil", 2013)
        assert result["champion"] == "Flamengo"

    def test_given_copa_do_brasil_2021_when_final_missing_then_no_champion(self, dataset):
        result = query.champion(dataset, "Copa do Brasil", 2021)
        assert result["champion"] is None
        assert "not present" in result["note"]


class TestCupBracket:
    """Scenario: Show the 2018 Copa Libertadores bracket
        Given knockout-stage matches
        When I build the bracket
        Then each round from the round of 16 to the final should appear
    """

    def test_given_libertadores_2018_when_building_bracket_then_all_knockout_rounds(self, dataset):
        result = query.bracket(dataset, "Libertadores", 2018)
        stages = [r["stage"] for r in result["rounds"]]
        assert stages == ["round of 16", "quarterfinal", "semifinal", "final"]
        round_of_16 = result["rounds"][0]
        assert len(round_of_16["ties"]) == 8
        final = result["rounds"][-1]
        assert final["ties"][0]["winner"] == "River Plate"

    def test_given_libertadores_2019_when_building_bracket_then_flamengo_beats_river(self, dataset):
        result = query.bracket(dataset, "Libertadores", 2019)
        final = result["rounds"][-1]
        assert final["ties"][0]["winner"] == "Flamengo"

    def test_given_copa_do_brasil_2020_when_building_bracket_then_palmeiras_champion(self, dataset):
        result = query.bracket(dataset, "Copa do Brasil", 2020)
        final = result["rounds"][-1]
        assert final["stage"] == "final"
        assert final["ties"][0]["winner"] == "Palmeiras"

    def test_given_a_league_when_building_bracket_then_error(self, dataset):
        with pytest.raises(QueryError, match="league"):
            query.bracket(dataset, "Serie A", 2019)


class TestCompetitionOverview:
    """Scenario: What data is available?
        Given the loaded dataset
        When I request an overview
        Then all competitions with coverage years should be listed
    """

    def test_given_dataset_when_overview_then_five_competitions_listed(self, dataset):
        result = query.competition_overview(dataset)
        names = {c["competition"] for c in result["competitions"]}
        assert names == {
            "Brasileirão Série A", "Brasileirão Série B", "Brasileirão Série C",
            "Copa do Brasil", "Copa Libertadores",
        }
        serie_a = next(c for c in result["competitions"] if c["competition"] == "Brasileirão Série A")
        assert serie_a["first_season"] == 2003
        assert serie_a["last_season"] == 2023
        assert result["players"] == 18207

    def test_given_unknown_competition_when_resolving_then_error_lists_available(self, dataset):
        with pytest.raises(query.CompetitionNotFoundError):
            query.standings(dataset, "Premier League", 2019)
