"""BDD scenarios for dataset loading and data coverage.

Feature: Data loading
  The MCP server loads every provided CSV dataset so that all six files
  are queryable, cross-file queries work and UTF-8 team names survive.
"""

from __future__ import annotations

import time

EXPECTED_SOURCES = {
    "brasileirao_matches",
    "novo_campeonato_brasileiro",
    "brazilian_cup_matches",
    "libertadores_matches",
    "br_football_dataset",
}


def test_all_six_datasets_are_loaded(data):
    """Scenario: Every provided CSV file is loaded
    Given the soccer knowledge base is loaded
    When the dataset inventory is inspected
    Then all five match datasets and the FIFA player dataset are present
    """
    # Given
    counts = data.dataset_stats()

    # When
    loaded_sources = {source for source in counts if source != "players"}

    # Then
    assert loaded_sources == EXPECTED_SOURCES
    assert counts["players"] == 18207
    assert len(data.matches) > 20000
    assert len(data.primary_matches) > 15000


def test_every_match_has_the_essential_fields(data):
    """Scenario: Match rows are complete
    Given the match data is loaded
    When any match is inspected
    Then it carries a competition, two teams and a source dataset
    """
    # Given
    matches = data.primary_matches

    # When
    sample = matches[:500]

    # Then
    for match in sample:
        assert match.competition
        assert match.home_team and match.away_team
        assert match.source
        assert match.home_team != match.away_team


def test_scores_are_parseable_for_played_matches(data):
    """Scenario: Goal columns become integers
    Given the match data is loaded
    When a played match is inspected
    Then both goal columns are integers, never strings or floats
    """
    # Given
    played = [m for m in data.primary_matches if m.is_played]

    # When
    totals = {m.total_goals for m in played[:1000]}

    # Then
    assert played
    assert all(isinstance(total, int) for total in totals)
    assert min(totals) >= 0


def test_utf8_names_survive_loading(data):
    """Scenario: Accented Portuguese names survive loading
    Given the datasets contain accented team names
    When the known teams are inspected
    Then names like São Paulo, Grêmio and Avaí keep their accents
    """
    # Given
    teams = set(data.known_teams.values())

    # When
    as_text = " | ".join(sorted(teams))

    # Then
    assert "São Paulo" in teams
    assert "Grêmio" in teams
    assert "Goiás" in teams
    assert "Criciúma" in as_text or "Criciúma" in teams


def test_primary_view_avoids_double_counting(data):
    """Scenario: Overlapping files do not duplicate a season
    Given the 2012-2019 Série A exists in two datasets
    When the de-duplicated primary view is inspected
    Then the 2019 season still has exactly 380 matches
    """
    # Given
    season_2019 = [
        m
        for m in data.primary_matches
        if m.competition == "Brasileirão Série A" and m.season == 2019
    ]

    # When
    raw_2019 = [
        m
        for m in data.matches
        if m.competition == "Brasileirão Série A" and m.season == 2019
    ]

    # Then
    assert len(raw_2019) == 3 * 380
    assert len(season_2019) == 380


def test_cross_file_player_and_match_queries(data):
    """Scenario: Player data joins with match data
    Given both match and player datasets are loaded
    When a club is resolved across both
    Then the same club name links matches and FIFA players
    """
    # Given
    club = "Grêmio"

    # When
    matches = data.primary_by_team.get(club, [])
    players = data.resolve_club_players(club)

    # Then
    assert matches
    assert players
    assert all(p.club == "Grêmio" for p in players)


def test_loading_is_fast_enough():
    """Scenario: Knowledge base loads within the performance budget
    Given the server starts up
    When all six datasets are parsed
    Then loading finishes well under the two second lookup budget
    """
    # Given
    from brazilian_soccer_mcp.loader import SoccerData

    # When
    start = time.perf_counter()
    fresh = SoccerData.load()
    elapsed = time.perf_counter() - start

    # Then
    assert fresh.players
    assert elapsed < 2.0
