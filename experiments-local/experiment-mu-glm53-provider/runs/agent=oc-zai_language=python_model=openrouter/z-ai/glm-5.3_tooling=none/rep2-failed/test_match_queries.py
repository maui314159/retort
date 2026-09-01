"""BDD scenarios for match queries (TASK.md "Match Queries").

Feature: Match Queries
  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition
"""

from __future__ import annotations

from data_loader import COPA_DO_BRASIL, LIBERTADORES, SERIE_A
from server import search_matches


class TestFindMatchesBetweenTwoTeams:
    """Gherkin: Flamengo vs Fluminense (Fla-Flu derby)."""

    def test_each_match_has_date_score_and_competition(self, data):
        """
        Scenario: Find matches between two teams
          Given the match data is loaded
          When I search for matches between "Flamengo" and "Fluminense"
          Then I should receive a list of matches
          And each match should have date, scores, and competition
        """
        # Given: data fixture
        # When
        result = search_matches(team="Flamengo", opponent="Fluminense")
        # Then
        assert result["data"]["total_matches"] > 30
        for match in result["data"]["matches"]:
            assert match["date"] is not None
            assert match["score"] is not None
            assert match["competition"] in {
                SERIE_A, COPA_DO_BRASIL, LIBERTADORES, "Brasileirão Série B",
            }
        assert "Flamengo" in result["summary"]
        assert "wins" in result["summary"]

    def test_head_to_head_summary_counts_meetings(self, data):
        """
        Scenario: head-to-head line in the summary
          Given Flamengo and Fluminense matches
          When I search matches between them
          Then the summary reports wins for both sides and draws
        """
        result = search_matches(team="Flamengo", opponent="Fluminense")
        assert "Flamengo" in result["summary"]
        assert "draws" in result["summary"]
        assert result["data"]["total_matches"] >= 40


class TestMatchesByTeamAndSeason:
    """Gherkin: 'What matches did Palmeiras play in 2023?'"""

    def test_palmeiras_2023_matches(self, data):
        """
        Scenario: matches by team and season
          Given the match data is loaded
          When I request Palmeiras matches for season 2023
          Then every returned match involves Palmeiras in 2023
        """
        result = search_matches(team="Palmeiras", season=2023)
        assert result["data"]["total_matches"] >= 30
        for match in result["data"]["matches"]:
            assert match["season"] == 2023
            assert "Palmeiras" in (match["home_team"], match["away_team"])

    def test_season_as_string_is_accepted(self, data):
        """
        Scenario: season given as text
          Given the season parameter "2023"
          When matches are searched
          Then it is interpreted as the year 2023
        """
        result = search_matches(team="Palmeiras", season="2023")
        assert all(m["season"] == 2023 for m in result["data"]["matches"])

    def test_matches_sorted_most_recent_first(self, data):
        """
        Scenario: ordering
          Given a match search by team
          When results are returned
          Then they are ordered most recent first
        """
        result = search_matches(team="Palmeiras", limit=50)
        dates = [m["date"] for m in result["data"]["matches"] if m["date"]]
        assert dates == sorted(dates, reverse=True)


class TestMatchesByCompetition:
    """Gherkin: 'Find all Copa do Brasil finals'."""

    def test_copa_do_brasil_finals(self, data):
        """
        Scenario: finals of a cup competition
          Given the match data is loaded
          When I search Copa do Brasil matches with stage "final"
          Then only final-round matches are returned
        """
        result = search_matches(competition="Copa do Brasil", stage="final")
        assert result["data"]["total_matches"] >= 10
        for match in result["data"]["matches"]:
            assert match["round"] == "Final"

    def test_libertadores_stage_filter(self, data):
        """
        Scenario: Libertadores stage filter
          Given Libertadores matches
          When filtering by stage "semifinals"
          Then only semifinal matches are returned
        """
        result = search_matches(competition="Libertadores", stage="semifinals")
        assert result["data"]["total_matches"] > 0
        assert all(m["stage"] == "semifinals" for m in result["data"]["matches"])

    def test_final_does_not_match_quarterfinal(self, data):
        """
        Scenario: stage filter precision
          Given matches labeled Quarterfinal and Final
          When filtering by stage "final"
          Then quarterfinals are excluded
        """
        result = search_matches(competition="Copa do Brasil", stage="final")
        rounds = {m["round"] for m in result["data"]["matches"]}
        assert "Quarterfinal" not in rounds


class TestMatchesByDateRange:
    """Gherkin: matches inside a date window."""

    def test_date_range_filters(self, data):
        """
        Scenario: date range search
          Given matches in June 2019
          When searching between 2019-06-01 and 2019-06-30
          Then every result falls inside the window
        """
        result = search_matches(
            competition="Brasileirão", date_from="2019-06-01", date_to="2019-06-30"
        )
        assert result["data"]["total_matches"] > 0
        for match in result["data"]["matches"]:
            assert "2019-06-01" <= match["date"] <= "2019-06-30"

    def test_brazilian_date_format_is_accepted(self, data):
        """
        Scenario: Brazilian date input
          Given date_from "01/06/2019" (DD/MM/YYYY)
          When searching Brasileirão matches
          Then results start on or after June 1st
        """
        result = search_matches(
            competition="Brasileirão", date_from="01/06/2019", date_to="10/06/2019"
        )
        assert result["data"]["total_matches"] > 0
        assert all(m["date"] >= "2019-06-01" for m in result["data"]["matches"])


class TestLastMatchBetweenTeams:
    """Gherkin: 'When did Flamengo last play Corinthians?'."""

    def test_most_recent_meeting(self, data):
        """
        Scenario: most recent meeting
          Given Flamengo and Corinthians fixtures
          When I search their matches
          Then the first result is the most recent meeting
        """
        result = search_matches(team="Flamengo", opponent="Corinthians", limit=1)
        first = result["data"]["matches"][0]
        assert first["score"] is not None
        assert first["competition"]
        dates = [m["date"] for m in search_matches(
            team="Flamengo", opponent="Corinthians", limit=100
        )["data"]["matches"] if m["date"]]
        assert first["date"] == max(dates)


class TestCrossFileDeduplication:
    """Scenarios: the same fixture must not appear twice."""

    def test_2019_serie_a_has_380_unique_matches(self, data):
        """
        Scenario: overlapping sources
          Given Série A 2019 exists in three source files
          When the data is loaded
          Then each fixture appears exactly once (380 matches)
        """
        matches = data.matches_by_competition(SERIE_A, 2019)
        assert len(matches) == 380

    def test_no_duplicate_fixture_in_any_league_season(self, data):
        """
        Scenario: dedup identity
          Given all league seasons
          When fixtures are grouped by season/round/home/away
          Then no group contains the same round fixture twice
        """
        for season in (2018, 2019, 2020, 2021, 2022):
            matches = data.matches_by_competition(SERIE_A, season)
            seen = set()
            for match in matches:
                if match.round is None or match.score is None:
                    continue
                key = (match.season, match.round, match.home_key, match.away_key)
                assert key not in seen, f"duplicate {key}"
                seen.add(key)


class TestTeamNameResolutionInQueries:
    """Scenarios: free-text team arguments."""

    def test_ambiguous_name_returns_candidates(self, data):
        """
        Scenario: ambiguous team name
          Given the query team "Atletico"
          When searching matches
          Then a disambiguation error lists Atlético-MG, Athletico-PR and
            Atlético-GO as candidates
        """
        result = search_matches(team="Atletico")
        assert "error" in result
        keys = {c["team_key"] for c in result["candidates"]}
        assert {"atletico-mg", "atletico-pr", "atletico-go"} <= keys

    def test_variant_spellings_find_the_same_matches(self, data):
        """
        Scenario: variant spellings
          Given "Palmeiras-SP", "Palmeiras" and "SE Palmeiras"
          When searching matches with each spelling
          Then identical result sets are returned
        """
        r1 = search_matches(team="Palmeiras-SP", season=2022)
        r2 = search_matches(team="Palmeiras", season=2022)
        r3 = search_matches(team="SE Palmeiras", season=2022)
        assert r1["data"]["total_matches"] == r2["data"]["total_matches"]
        assert r2["data"]["total_matches"] == r3["data"]["total_matches"]
        assert r1["data"]["total_matches"] > 0

    def test_unknown_team_returns_error(self, data):
        """
        Scenario: unknown team
          Given the team "Real Madrid Basketball"
          When searching matches
          Then a helpful error is returned
        """
        result = search_matches(team="Real Madrid Basketball")
        assert "error" in result
