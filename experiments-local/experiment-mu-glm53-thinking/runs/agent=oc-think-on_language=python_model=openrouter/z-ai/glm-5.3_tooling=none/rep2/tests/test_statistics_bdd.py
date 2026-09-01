"""BDD scenarios for statistical analysis.

Feature: Statistical analysis
  Aggregated statistics: goals per match, home vs away performance,
  biggest wins and season comparisons.
"""

from __future__ import annotations

import pytest

SERIE_A = "Brasileirão Série A"


def test_average_goals_per_match(service):
    """Scenario: What's the average goals per match in the Brasileirão?
    Given every Série A result since 2003 is loaded
    When I ask for the goals summary
    Then goals per match, home/draw/away rates are all reported
    """
    # Given / When
    stats = service.stats_summary(competition=SERIE_A)

    # Then
    assert stats["matches"] == 8401
    assert stats["average_goals_per_match"] == 2.57
    assert stats["total_goals"] > 20000
    assert abs(stats["total_goals"] / stats["matches"] - 2.57) < 0.01
    home = stats["home_win_rate"]
    draw = stats["draw_rate"]
    away = stats["away_win_rate"]
    assert home + draw + away == pytest.approx(100.0, abs=0.2)
    assert stats["home_wins"] + stats["away_wins"] + stats["draws"] == stats["matches"]
    assert 40 <= home <= 60
    assert 20 <= away <= 40


def test_average_goals_per_season(service):
    """Scenario: Average goals for one season
    Given the 2019 Série A averaged roughly 2.3 goals per game
    When I ask for that season's summary
    Then the numbers reflect only 2019 matches
    """
    # Given / When
    stats = service.stats_summary(competition=SERIE_A, season=2019)

    # Then
    assert stats["matches"] == 380
    assert 2.0 <= stats["average_goals_per_match"] <= 2.7
    assert stats["total_goals"] == 876
    assert stats["total_goals"] == sum(
        m.total_goals
        for m in service.data.primary_matches
        if m.competition == SERIE_A and m.season == 2019 and m.is_played
    )


def test_home_advantage_exists(service):
    """Scenario: Home vs away performance
    Given home teams traditionally win about half the matches
    When the overall rates are computed
    Then the home win rate clearly exceeds the away win rate
    """
    # Given / When
    stats = service.stats_summary(competition=SERIE_A)

    # Then
    assert stats["home_win_rate"] > stats["away_win_rate"]
    assert stats["home_wins"] > stats["away_wins"]


def test_biggest_wins_in_dataset(service):
    """Scenario: Show me the biggest wins in the dataset
    Given every match in the knowledge base
    When I ask for the biggest wins
    Then they are ranked by goal margin, largest first
    """
    # Given / When
    result = service.biggest_wins(limit=5)

    # Then
    assert result["matches"]
    margins = [
        abs(m["home_goals"] - m["away_goals"]) for m in result["matches"]
    ]
    assert margins == sorted(margins, reverse=True)
    assert margins[0] >= 8
    assert result["matches"][0]["competition"] == "Copa Libertadores"


def test_biggest_serie_a_wins(service):
    """Scenario: Biggest wins restricted to the Brasileirão
    Given the biggest Série A home win in the data is Goiás 7-0 Juventude
    When I filter biggest wins to the Série A
    Then only league matches appear, ranked by margin
    """
    # Given / When
    result = service.biggest_wins(competition=SERIE_A, limit=3)

    # Then
    assert all(m["competition"] == SERIE_A for m in result["matches"])
    top = result["matches"][0]
    assert (top["home_team"], top["away_team"]) == ("Goiás", "Juventude")
    assert (top["home_goals"], top["away_goals"]) == (7, 0)


def test_season_comparison(service):
    """Scenario: Compare the 2018 and 2019 seasons
    Given two full Série A seasons
    When I compare them
    Then both season summaries and the goals delta come back
    """
    # Given
    first, second = 2018, 2019

    # When
    comparison = service.season_comparison(first, second, competition=SERIE_A)

    # Then
    assert comparison["season_a"]["season"] == 2018
    assert comparison["season_b"]["season"] == 2019
    assert comparison["season_a"]["matches"] == 380
    assert comparison["season_b"]["matches"] == 380
    assert comparison["average_goals_delta"] == round(
        comparison["season_b"]["average_goals_per_match"]
        - comparison["season_a"]["average_goals_per_match"],
        2,
    )
    assert "2018 vs 2019" in comparison["summary"]


def test_head_to_head_is_symmetric(service):
    """Scenario: Head-to-head from both sides
    Given Palmeiras and Santos have a long rivalry
    When I ask from either side
    Then the same totals come back with mirrored win counts
    """
    # Given / When
    from_palmeiras = service.head_to_head("Palmeiras", "Santos")
    from_santos = service.head_to_head("Santos", "Palmeiras")

    # Then
    assert from_palmeiras["total_matches"] == from_santos["total_matches"] == 41
    assert from_palmeiras["team_a_wins"] == from_santos["team_b_wins"]
    assert from_palmeiras["team_b_wins"] == from_santos["team_a_wins"]
    assert from_palmeiras["draws"] == from_santos["draws"]


def test_extended_match_statistics_available(service):
    """Scenario: Corner and shot statistics
    Given the BR-Football dataset records corners, shots and attacks
    When a covered match is inspected
    Then the extended statistics are attached
    """
    # Given / When
    result = service.find_matches(team="Flamengo", season=2019, limit=50)

    # Then
    with_stats = [
        m for m in result["matches"] if m["stats"]["home_corners"] is not None
    ]
    assert with_stats, "expected at least one match with extended stats"
    for match in with_stats:
        stats = match["stats"]
        assert stats["home_shots"] is not None or stats["away_shots"] is not None
        assert stats["home_corners"] >= 0


def test_query_performance_budgets(service):
    """Scenario: Response time budgets
    Given simple lookups must answer in under 2 seconds
    And aggregate queries in under 5 seconds
    When representative queries run
    Then every one finishes inside its budget
    """
    # Given
    import time

    simple = [
        lambda: service.last_meeting("Flamengo", "Corinthians"),
        lambda: service.search_players(nationality="Brazil"),
    ]
    aggregates = [
        lambda: service.standings(SERIE_A, 2019),
        lambda: service.head_to_head("Flamengo", "Fluminense"),
        lambda: service.best_records(venue="away"),
        lambda: service.biggest_wins(),
        lambda: service.derbies(),
    ]

    # When / Then
    for query in simple:
        start = time.perf_counter()
        query()
        assert time.perf_counter() - start < 2.0
    for query in aggregates:
        start = time.perf_counter()
        query()
        assert time.perf_counter() - start < 5.0
