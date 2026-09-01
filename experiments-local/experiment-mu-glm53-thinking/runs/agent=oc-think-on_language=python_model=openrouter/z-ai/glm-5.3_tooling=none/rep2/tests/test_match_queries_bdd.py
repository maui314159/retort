"""BDD scenarios for match queries.

Feature: Match queries
  Users ask for matches by team, opponent, competition, season, date
  range and stage, for head-to-head records and for last meetings.
"""

from __future__ import annotations

SERIE_A = "Brasileirão Série A"


def test_matches_between_two_teams(service):
    """Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition
    """
    # Given
    team_a, team_b = "Flamengo", "Fluminense"

    # When
    result = service.head_to_head(team_a, team_b)

    # Then
    assert result["total_matches"] == 44
    assert result["team_a_wins"] + result["team_b_wins"] + result["draws"] == 44
    for match in result["matches"]:
        assert match["date"] is not None
        assert match["home_goals"] is not None
        assert match["away_goals"] is not None
        assert match["competition"] in (
            SERIE_A,
            "Copa do Brasil",
            "Copa Libertadores",
        )


def test_head_to_head_summary_counts(service):
    """Scenario: Head-to-head record
    Given Flamengo and Fluminense have met many times
    When I ask for their head-to-head record
    Then wins, draws and losses for both sides are reported
    """
    # Given / When
    result = service.head_to_head("Flamengo", "Fluminense")

    # Then
    assert result["team_a"] == "Flamengo"
    assert result["team_b"] == "Fluminense"
    assert result["team_a_wins"] == 18
    assert result["team_b_wins"] == 14
    assert result["draws"] == 12


def test_head_to_head_resolves_name_variants(service):
    """Scenario: Name variants in head-to-head queries
    Given users may type "Flamengo-RJ" or "Fluminense-RJ"
    When I ask for the head-to-head
    Then the clubs resolve and the same record comes back
    """
    # Given / When
    result = service.head_to_head("Flamengo-RJ", "Fluminense-RJ")

    # Then
    assert result["team_a"] == "Flamengo"
    assert result["team_b"] == "Fluminense"
    assert result["total_matches"] == 44


def test_matches_by_team_and_season(service):
    """Scenario: Matches for one team in one season
    Given Palmeiras played in 2023
    When I search for Palmeiras matches in season 2023
    Then a full season of matches is returned
    """
    # Given / When
    result = service.find_matches(team="Palmeiras", season=2023)

    # Then
    assert result["total"] == 43
    competitions = {m["competition"] for m in result["matches"]}
    assert competitions
    assert all(m["season"] == 2023 for m in result["matches"])
    assert all(
        "Palmeiras" in (m["home_team"], m["away_team"]) for m in result["matches"]
    )


def test_matches_by_date_range(service):
    """Scenario: Date range filter
    Given Flamengo played several matches in September 2023
    When I search between 2023-09-01 and 2023-09-30
    Then only matches inside the range are returned
    """
    # Given
    start, end = "2023-09-01", "2023-09-30"

    # When
    result = service.find_matches(team="Flamengo", date_from=start, date_to=end)

    # Then
    assert result["total"] == 6
    for match in result["matches"]:
        assert start <= match["date"] <= end


def test_matches_by_competition(service):
    """Scenario: Competition filter
    Given the dataset holds Brasileirão, Copa do Brasil and Libertadores
    When I search only the Libertadores
    Then every result is a Libertadores match
    """
    # Given / When
    result = service.find_matches(competition="Copa Libertadores", season=2019, limit=200)

    # Then
    assert result["total"] > 100
    assert all(m["competition"] == "Copa Libertadores" for m in result["matches"])
    assert all(m["season"] == 2019 for m in result["matches"])


def test_copa_do_brasil_finals(service):
    """Scenario: Find all Copa do Brasil finals
    Given the cup dataset labels the final round
    When I search for finals in the 2013 Copa do Brasil
    Then the two-legged final between Flamengo and Athletico is returned
    """
    # Given / When
    result = service.find_matches(competition="Copa do Brasil", season=2013, stage="final")

    # Then
    assert result["total"] == 2
    teams = set()
    for match in result["matches"]:
        assert match["round"] == "Final"
        teams.update([match["home_team"], match["away_team"]])
    assert teams == {"Flamengo", "Athletico Paranaense"}
    scores = sorted(
        (match["home_team"], match["home_goals"], match["away_goals"])
        for match in result["matches"]
    )
    assert ("Flamengo", 2, 0) in scores
    assert ("Athletico Paranaense", 1, 1) in scores


def test_libertadores_final_2019(service):
    """Scenario: The 2019 Libertadores final
    Given Flamengo beat River Plate 2-1 in the 2019 final
    When I search Libertadores 2019 finals
    Then that single-match final is returned
    """
    # Given / When
    result = service.find_matches(competition="Copa Libertadores", season=2019, stage="final")

    # Then
    assert result["total"] == 1
    final = result["matches"][0]
    assert final["home_team"] == "Flamengo"
    assert final["away_team"] == "River Plate (ARG)"
    assert final["home_goals"] == 2 and final["away_goals"] == 1


def test_last_meeting_between_teams(service):
    """Scenario: Last meeting
    Given Flamengo and Corinthians met in 2023
    When I ask when they last played and what the score was
    Then the most recent match with its score is returned
    """
    # Given / When
    result = service.last_meeting("Flamengo", "Corinthians")

    # Then
    match = result["match"]
    assert match["date"] == "2023-10-08"
    assert match["home_team"] == "Corinthians"
    assert match["away_team"] == "Flamengo"
    assert (match["home_goals"], match["away_goals"]) == (1, 1)


def test_last_meeting_is_the_latest(service):
    """Scenario: Last meeting is newer than every other meeting
    Given the full meeting history of two teams
    When I ask for the last meeting
    Then its date is the maximum across all their matches
    """
    # Given
    history = service.head_to_head("Palmeiras", "Santos", limit=200)["matches"]

    # When
    latest = service.last_meeting("Palmeiras", "Santos")["match"]

    # Then
    assert latest["date"] == max(m["date"] for m in history)


def test_home_and_away_filters(service):
    """Scenario: Venue filter
    Given a team plays home and away fixtures
    When I restrict the search to away matches
    Then only away fixtures are returned
    """
    # Given / When
    result = service.find_matches(
        team="Corinthians", competition=SERIE_A, season=2019, venue="away"
    )

    # Then
    assert result["total"] == 19
    assert all(m["away_team"] == "Corinthians" for m in result["matches"])


def test_season_pair_meetings_in_league(service):
    """Scenario: League pairs meet twice per season
    Given Série A teams play each other twice a season
    When I search the 2019 Flamengo-Fluminense league meetings
    Then exactly two matches are found, one at each ground
    """
    # Given / When
    result = service.find_matches(
        team="Flamengo", opponent="Fluminense", competition=SERIE_A, season=2019
    )

    # Then
    assert result["total"] == 2
    home_sides = {m["home_team"] for m in result["matches"]}
    assert home_sides == {"Flamengo", "Fluminense"}


def test_derbies_in_a_season(service):
    """Scenario: Show me all derbies in 2023
    Given the knowledge base knows the traditional rivalries
    When I ask for derbies in 2023
    Then matches for Fla-Flu, Grenal and the Derby Paulista are found
    """
    # Given / When
    result = service.derbies(season=2023)

    # Then
    names = {block["derby"] for block in result["derbies"]}
    assert {"Fla-Flu", "Grenal", "Derby Paulista", "Clássico Mineiro"} <= names
    assert result["match_count"] == 26
    for block in result["derbies"]:
        for match in block["recent"]:
            home, away = match["home_team"], match["away_team"]
            assert {home, away} == set(block["teams"])


def test_unknown_team_raises_helpful_error(service):
    """Scenario: Unknown team name
    Given a user asks about a team that does not exist
    When the query runs
    Then a clear error naming the team is raised
    """
    # Given
    bogus = "Real Madrid Basketball Team"

    # When / Then
    try:
        service.find_matches(team=bogus)
    except ValueError as error:
        assert bogus in str(error)
    else:
        raise AssertionError("expected ValueError for unknown team")
