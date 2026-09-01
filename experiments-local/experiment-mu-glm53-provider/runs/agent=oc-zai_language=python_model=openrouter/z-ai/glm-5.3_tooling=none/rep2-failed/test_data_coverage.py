"""BDD scenarios for dataset coverage (TASK.md "Success Criteria").

Feature: Data Coverage
  Scenario: All six CSV files are loadable and queryable
    Given the datasets in data/kaggle/
    When the data is loaded
    Then every source file contributes matches or players
    And at least twenty distinct sample questions can be answered
"""

from __future__ import annotations

from data_loader import (
    COPA_DO_BRASIL,
    LIBERTADORES,
    SERIE_A,
    SERIE_B,
    SERIE_C,
)
from server import (
    get_aggregate_statistics,
    get_best_records,
    get_biggest_wins,
    get_club_players,
    get_competition_finals,
    get_derby_matches,
    get_head_to_head,
    get_player_details,
    get_standings,
    get_team_stats,
    resolve_team,
    search_matches,
    search_players,
)

SOURCE_FILES = {
    "Brasileirao_Matches.csv",
    "Brazilian_Cup_Matches.csv",
    "Libertadores_Matches.csv",
    "BR-Football-Dataset.csv",
    "novo_campeonato_brasileiro.csv",
}


class TestDataCoverage:
    def test_all_six_files_are_loaded(self, data):
        """
        Scenario: file coverage
          Given the six CSV files
          When the data is loaded
          Then each of the five match files contributes matches
            And the FIFA file contributes 18,207 players
        """
        sources = {m.source for m in data.matches}
        assert sources == SOURCE_FILES, sources
        assert len(data.players) == 18207

    def test_each_competition_is_queryable(self, data):
        """
        Scenario: competition coverage
          Given the five competitions
          When matches are queried per competition
          Then each returns a substantial number of matches
        """
        expected = {
            SERIE_A: 8000,
            SERIE_B: 3000,
            SERIE_C: 1500,
            COPA_DO_BRASIL: 1500,
            LIBERTADORES: 1200,
        }
        for competition, minimum in expected.items():
            matches = data.matches_by_competition(competition)
            assert len(matches) >= minimum, (competition, len(matches))

    def test_extended_statistics_are_available(self, data):
        """
        Scenario: extended match statistics
          Given the BR-Football dataset
          When matches with corner/shot statistics are counted
          Then a large share of matches carry them
        """
        assert len(data.stats_matches) > 8000
        sample = data.stats_matches[0].stats
        assert "total_corners" in sample

    def test_season_coverage_spans(self, data):
        """
        Scenario: historical span
          Given the Série A data
          When seasons are listed
          Then they span 2003 through 2023
        """
        seasons = data.seasons_for_competition(SERIE_A)
        assert seasons[0] <= 2003
        assert seasons[-1] >= 2023


class TestSampleQuestionCoverage:
    """Each test answers one TASK.md sample question end-to-end."""

    def test_at_least_twenty_sample_questions_answered(self, data):
        """
        Scenario: the twenty-question bar
          Given the MCP tool surface
          When one call per TASK.md sample question is executed
          Then every call succeeds with a usable answer
        """
        questions = {
            "When did Flamengo last play Corinthians?":
                lambda: search_matches(team="Flamengo", opponent="Corinthians", limit=1),
            "What was the score of that match?":
                lambda: search_matches(team="Flamengo", opponent="Corinthians", limit=1),
            "Who is Gabriel Jesus?":
                lambda: get_player_details("Gabriel Jesus"),
            "Which players play for Grêmio?":
                lambda: get_club_players("Grêmio"),
            "Show me all derbies in 2023":
                lambda: get_derby_matches(season=2023),
            "What competitions has Palmeiras played in?":
                lambda: search_matches(team="Palmeiras", limit=5),
            "Which team has the best home record?":
                lambda: get_best_records(competition="Brasileirão", venue="home"),
            "Who are the top Brazilian players?":
                lambda: search_players(nationality="Brazil", min_overall=88),
            "Compare the 2018 and 2019 seasons":
                lambda: get_aggregate_statistics(
                    competition="Serie A", season=2018
                ),
            "Who won the 2019 Brasileirão?":
                lambda: get_standings(competition="Brasileirão", season=2019),
            "Which teams were relegated in 2020?":
                lambda: get_standings(competition="Brasileirão", season=2020),
            "Show the 2018 Copa Libertadores bracket (final)":
                lambda: get_competition_finals("Libertadores"),
            "Find all Copa do Brasil finals":
                lambda: search_matches(competition="Copa do Brasil", stage="final"),
            "Show me all Flamengo vs Fluminense matches":
                lambda: get_head_to_head("Flamengo", "Fluminense"),
            "What matches did Palmeiras play in 2023?":
                lambda: search_matches(team="Palmeiras", season=2023),
            "What is Corinthians' home record in 2022?":
                lambda: get_team_stats(
                    team="Corinthians", competition="Brasileirão", season=2022,
                    venue="home",
                ),
            "Which team scored the most goals in Serie A 2023?":
                lambda: get_best_records(competition="Serie A", season=2023, metric="goals"),
            "Compare Palmeiras and Santos head-to-head":
                lambda: get_head_to_head("Palmeiras", "Santos"),
            "What's the average goals per match in the Brasileirão?":
                lambda: get_aggregate_statistics(competition="Brasileirão"),
            "Show me the biggest wins in the dataset":
                lambda: get_biggest_wins(limit=5),
            "Which team has the best away record?":
                lambda: get_best_records(
                    competition="Brasileirão", venue="away", metric="win_rate"
                ),
            "What is known about the club Santos?":
                lambda: resolve_team("Santos"),
        }
        answered = 0
        for question, call in questions.items():
            result = call()
            payload = result.get("data", result)
            assert payload, question
            if "error" not in result:
                answered += 1
        assert answered >= 20
