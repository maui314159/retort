"""BDD scenarios for team queries.

Feature: Team queries
  Users ask for match histories, win/loss/draw records, goals, home and
  away splits, and comparisons between teams.
"""

from __future__ import annotations

SERIE_A = "Brasileirão Série A"


def test_team_record_in_season(service):
    """Scenario: Get team statistics
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season "2019"
    Then I should receive wins, losses, draws, and goals
    """
    # Given
    team, season = "Palmeiras", 2019

    # When
    record = service.team_record(team, competition=SERIE_A, season=season)

    # Then
    assert record["matches"] == 38
    assert record["wins"] == 21
    assert record["draws"] == 11
    assert record["losses"] == 6
    assert record["goals_for"] == 61
    assert record["goals_against"] == 32
    assert record["wins"] + record["draws"] + record["losses"] == record["matches"]


def test_team_home_record_in_season(service):
    """Scenario: What is Corinthians' home record in 2022?
    Given Corinthians played 19 home matches in the 2022 Série A
    When I request their home record
    Then matches, wins, draws, losses and goals come back
    """
    # Given
    team, season = "Corinthians", 2022

    # When
    record = service.team_record(team, competition=SERIE_A, season=season, venue="home")

    # Then
    assert record["matches"] == 19
    assert record["wins"] == 12
    assert record["draws"] == 4
    assert record["losses"] == 3
    assert record["goals_for"] == 24
    assert record["goals_against"] == 11
    assert record["win_rate"] == 63.2


def test_home_and_away_records_split_correctly(service):
    """Scenario: Home plus away equals the full record
    Given a team plays home and away fixtures
    When home and away records are computed
    Then their sums match the all-venue record
    """
    # Given
    team, season = "Flamengo", 2019

    # When
    total = service.team_record(team, competition=SERIE_A, season=season)
    home = service.team_record(
        team, competition=SERIE_A, season=season, venue="home"
    )
    away = service.team_record(
        team, competition=SERIE_A, season=season, venue="away"
    )

    # Then
    assert total["matches"] == home["matches"] + away["matches"] == 38
    assert total["wins"] == home["wins"] + away["wins"]
    assert total["goals_for"] == home["goals_for"] + away["goals_for"]
    assert home["matches"] == away["matches"] == 19


def test_team_record_accepts_name_variants(service):
    """Scenario: Team statistics with state suffix
    Given users may type "Corinthians-SP"
    When the record is requested
    Then the same club record comes back
    """
    # Given / When
    with_suffix = service.team_record("Corinthians-SP", season=2019)
    without_suffix = service.team_record("Corinthians", season=2019)

    # Then
    assert with_suffix == without_suffix
    assert with_suffix["team"] == "Corinthians"


def test_team_profile_spans_competitions(service):
    """Scenario: What competitions has Palmeiras played in?
    Given Palmeiras appears in several datasets
    When I request the club profile
    Then all its competitions, seasons and records are returned
    """
    # Given / When
    profile = service.team_profile("Palmeiras")

    # Then
    assert set(profile["competitions"]) == {SERIE_A, "Copa do Brasil", "Copa Libertadores"}
    expected_serie_a_seasons = [y for y in range(2004, 2024) if y != 2013]
    assert profile["competitions"][SERIE_A] == expected_serie_a_seasons
    assert profile["record"]["matches"] == 888
    assert profile["home_record"]["matches"] + profile["away_record"]["matches"] == 888
    assert profile["first_match"].startswith("2004-")
    assert profile["last_match"].startswith("2023-")


def test_list_teams_for_a_season(service):
    """Scenario: Teams in a season
    Given twenty clubs played the 2019 Série A
    When I list the teams of that season
    Then all twenty are returned, including Flamengo
    """
    # Given / When
    result = service.list_teams(competition=SERIE_A, season=2019)

    # Then
    assert result["summary"] == "20 teams found"
    assert "Flamengo" in result["teams"]
    assert len(result["teams"]) == 20


def test_best_away_record(service):
    """Scenario: Which team has the best away record?
    Given every team's away record can be computed
    When I ask for the best away records
    Then teams are ranked by away win rate
    """
    # Given / When
    result = service.best_records(competition=SERIE_A, venue="away", limit=5)

    # Then
    records = result["records"]
    assert len(records) == 5
    rates = [r["wins"] / r["matches"] for r in records]
    assert rates == sorted(rates, reverse=True)
    for record in records:
        assert record["matches"] >= 5
        assert record["matches"] % 1 == 0


def test_best_home_record(service):
    """Scenario: Which team has the best home record?
    Given every team's home record can be computed
    When I ask for the best home records
    Then teams are ranked by home win rate
    """
    # Given / When
    result = service.best_records(competition=SERIE_A, venue="home", limit=3)

    # Then
    assert len(result["records"]) == 3
    top = result["records"][0]
    assert top["win_rate"] >= result["records"][1]["win_rate"]


def test_team_record_across_all_competitions(service):
    """Scenario: Record without filters
    Given a team played in several competitions
    When no competition or season filter is given
    Then the aggregate record covers every primary match
    """
    # Given / When
    record = service.team_record("Vasco da Gama")

    # Then
    breakdown = record["breakdown_by_competition"]
    assert {row["competition"] for row in breakdown} >= {SERIE_A, "Copa do Brasil"}
    total_from_breakdown = sum(row["matches"] for row in breakdown)
    assert total_from_breakdown == record["matches"]
