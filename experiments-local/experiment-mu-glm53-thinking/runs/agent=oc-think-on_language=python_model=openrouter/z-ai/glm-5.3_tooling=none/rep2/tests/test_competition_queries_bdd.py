"""BDD scenarios for competition queries.

Feature: Competition queries
  Standings are calculated from match results, so champions, relegated
  teams and season inventories can be derived from the datasets.
"""

from __future__ import annotations

import pytest

SERIE_A = "Brasileirão Série A"

#: Champions of the Série A by season (historical ground truth).
KNOWN_CHAMPIONS = {
    2003: "Cruzeiro",
    2004: "Santos",
    2005: "Corinthians",
    2009: "Flamengo",
    2012: "Fluminense",
    2015: "Corinthians",
    2016: "Palmeiras",
    2019: "Flamengo",
    2020: "Flamengo",
    2021: "Atlético Mineiro",
    2022: "Palmeiras",
}


def test_standings_for_a_season(service):
    """Scenario: Who won the 2019 Brasileirão?
    Given the 2019 Série A results are loaded
    When I compute the standings
    Then Flamengo is champion with 90 points from 28 wins, 6 draws, 4 losses
    """
    # Given / When
    table = service.standings(SERIE_A, 2019)

    # Then
    assert table["champion"] == "Flamengo"
    assert table["matches_used"] == 380
    assert table["complete"] is True
    top = table["table"][0]
    assert top["team"] == "Flamengo"
    assert top["points"] == 90
    assert (top["wins"], top["draws"], top["losses"]) == (28, 6, 4)
    assert top["note"] == "Champion"


@pytest.mark.parametrize("season,expected", sorted(KNOWN_CHAMPIONS.items()))
def test_champions_by_season(service, season, expected):
    """Scenario Outline: Champions by season
    Given the Série A has run every year in the dataset
    When I compute the standings for <season>
    Then <expected> is champion
    """
    # Given / When
    table = service.standings(SERIE_A, season)

    # Then
    assert table["champion"] == expected
    positions = [row["position"] for row in table["table"]]
    assert positions == list(range(1, len(positions) + 1))


def test_relegated_teams_2022(service):
    """Scenario: Which teams were relegated in 2022?
    Given the bottom four of the 2022 Série A were relegated
    When I compute the standings
    Then those four teams are flagged
    """
    # Given / When
    table = service.standings(SERIE_A, 2022)

    # Then
    assert set(table["relegated"]) == {
        "Ceará",
        "Atlético Goianiense",
        "Avaí",
        "Juventude",
    }
    assert table["table"][-1]["note"] == "Relegated"


def test_relegated_teams_2020(service):
    """Scenario: Relegation in 2020
    Given Vasco, Goiás, Coritiba and Botafogo went down in 2020
    When I compute the standings
    Then those four teams are flagged as relegated
    """
    # Given / When
    table = service.standings(SERIE_A, 2020)

    # Then
    assert set(table["relegated"]) == {
        "Vasco da Gama",
        "Goiás",
        "Coritiba",
        "Botafogo",
    }


def test_standings_are_sorted_by_points(service):
    """Scenario: Table ordering
    Given a computed league table
    When the rows are inspected
    Then they descend by points, then goal difference, then goals for
    """
    # Given / When
    table = service.standings(SERIE_A, 2021)["table"]

    # Then
    keys = [
        (-row["points"], -row["goal_difference"], -row["goals_for"])
        for row in table
    ]
    assert keys == sorted(keys)


def test_standings_reject_unknown_competition(service):
    """Scenario: Unknown competition
    Given a user asks for a competition that does not exist
    When standings are requested
    Then a clear error lists the known competitions
    """
    # Given
    bogus = "Premier League"

    # When / Then
    with pytest.raises(ValueError, match="Unknown competition"):
        service.standings(bogus, 2019)


def test_standings_for_season_without_data(service):
    """Scenario: Season without data
    Given no dataset covers the 1999 Série A
    When standings are requested
    Then a clear error is raised
    """
    # Given / When / Then
    with pytest.raises(ValueError, match="No data"):
        service.standings(SERIE_A, 1999)


def test_competition_info_lists_everything(service):
    """Scenario: What data do you have?
    Given five competitions are loaded
    When I ask for the competition inventory
    Then each comes back with its seasons and match counts
    """
    # Given / When
    info = service.competition_info()

    # Then
    competitions = info["competitions"]
    assert set(competitions) == {
        SERIE_A,
        "Brasileirão Série B",
        "Brasileirão Série C",
        "Copa do Brasil",
        "Copa Libertadores",
    }
    assert competitions[SERIE_A]["seasons"] == list(range(2003, 2024))
    assert competitions["Copa Libertadores"]["seasons"][0] == 2013
    assert competitions[SERIE_A]["matches"] == 8402


def test_serie_b_seasons_available(service):
    """Scenario: Série B coverage
    Given the BR-Football dataset covers Série B
    When I ask which seasons exist
    Then the list starts in 2014
    """
    # Given / When
    info = service.competition_info(competition="Série B")

    # Then
    seasons = info["competitions"]["Brasileirão Série B"]["seasons"]
    assert seasons[0] == 2014
    assert seasons[-1] == 2023


def test_libertadores_season_attribution(service):
    """Scenario: COVID-delayed Libertadores final
    Given the 2020 Libertadores final was played in January 2021
    When I look up the 2020 final
    Then it is still attributed to the 2020 season
    """
    # Given / When
    result = service.find_matches(
        competition="Copa Libertadores", season=2020, stage="final"
    )

    # Then
    assert result["total"] == 1
    final = result["matches"][0]
    assert final["home_team"] == "Palmeiras"
    assert final["away_team"] == "Santos"
    assert (final["home_goals"], final["away_goals"]) == (1, 0)


def test_serie_a_2023_flagged_incomplete(service):
    """Scenario: Incomplete season data is disclosed
    Given the 2023 Série A is partially covered by the datasets
    When I compute the standings
    Then the result flags the season as incomplete
    """
    # Given / When
    table = service.standings(SERIE_A, 2023)

    # Then
    assert table["complete"] is False
    assert table["matches_used"] < 380
    assert "incomplete" in table["summary"]
