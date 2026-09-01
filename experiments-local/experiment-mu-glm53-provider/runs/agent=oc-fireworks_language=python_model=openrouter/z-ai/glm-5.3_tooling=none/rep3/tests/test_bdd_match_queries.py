"""Feature: Match Queries (BDD)

Spec scenarios:

    Scenario: Find matches between two teams
      Given the match data is loaded
      When I search for matches between "Flamengo" and "Fluminense"
      Then I should receive a list of matches
      And each match should have date, scores, and competition

    Scenario: Get team statistics
      Given the match data is loaded
      When I request statistics for "Palmeiras" in season "2023"
      Then I should receive wins, losses, draws, and goals
"""

from __future__ import annotations

import pytest

from brsoccer import queries as q

pytestmark = pytest.mark.bdd


class TestFindMatchesBetweenTwoTeams:
    """Scenario: Find matches between two teams."""

    def test_when_searching_flamengo_vs_fluminense(self, sd):
        # Given the match data is loaded
        # When I search for matches between "Flamengo" and "Fluminense"
        matches = q.find_matches(sd, team="Flamengo", opponent="Fluminense")
        # Then I should receive a list of matches
        assert len(matches) >= 40
        # And each match should have date, scores, and competition
        for match in matches:
            assert match.date is not None
            assert match.competition in ("serie_a", "copa_do_brasil", "serie_b", "serie_c", "libertadores")
            assert match.home_display and match.away_display
        # And both teams must always be the ones asked for (any spelling)
        flamengo = q.resolve_team(sd, "Flamengo")
        fluminense = q.resolve_team(sd, "Fluminense")
        for match in matches:
            assert match.is_between(flamengo, fluminense)

    def test_results_are_most_recent_first(self, sd):
        # When I search for all matches of "Corinthians"
        matches = q.find_matches(sd, team="Corinthians")
        # Then they come back newest first
        dates = [m.date for m in matches if m.date]
        assert dates == sorted(dates, reverse=True)


class TestFindMatchesByTeamAndSeason:
    """Scenario: What matches did Palmeiras play in 2023?"""

    def test_palmeiras_2023_matches(self, sd):
        # When I request Palmeiras matches for season 2023
        matches = q.find_matches(sd, team="Palmeiras", season=2023)
        # Then every match is from 2023 and involves Palmeiras
        assert len(matches) >= 30
        palmeiras = q.resolve_team(sd, "Palmeiras")
        for match in matches:
            assert match.season == 2023
            assert match.involves(palmeiras)

    def test_palmeiras_2023_is_from_the_brf_source(self, sd):
        # And 2023 coverage comes from the BR-Football dataset
        # (the only file with 2023 matches).
        matches = q.find_matches(sd, team="Palmeiras", season=2023)
        assert all(m.source == "BR-Football-Dataset.csv" for m in matches)


class TestFindMatchesByDateRange:
    """Scenario: Find matches by date range."""

    def test_date_range_filter(self, sd):
        # When I search for matches in May 2019
        matches = q.find_matches(sd, date_from="2019-05-01", date_to="2019-05-31")
        # Then every match falls inside the range
        assert len(matches) > 50
        for match in matches:
            assert match.date.year == 2019
            assert match.date.month == 5


class TestFindMatchesByCompetitionAndStage:
    """Scenario: Find all Copa do Brasil finals."""

    def test_copa_do_brasil_finals(self, sd):
        # When I search Copa do Brasil matches in stage "8" (the Final)
        finals = q.find_matches(sd, competition="copa_do_brasil", stage="8")
        # Then I receive the finals: 14 two-legged finals
        assert len(finals) == 14
        seasons = {m.season for m in finals}
        assert 2013 in seasons and 2020 in seasons

    def test_copa_final_alias_is_final(self, sd):
        # And asking for stage "final" finds the same matches
        by_word = q.find_matches(sd, competition="copa_do_brasil", stage="final")
        assert len(by_word) == 14

    def test_libertadores_finals(self, sd):
        # When I search Libertadores finals
        finals = q.find_matches(sd, competition="libertadores", stage="final")
        # Then finals exist from 2013 (two legs) and 2019+ (single leg)
        assert {m.season for m in finals} >= {2013, 2014, 2018, 2019, 2020}
        flamengo_river = [m for m in finals if m.season == 2019]
        assert len(flamengo_river) == 1
        assert flamengo_river[0].home_display == "Flamengo"
        assert (flamengo_river[0].home_goal, flamengo_river[0].away_goal) == (2, 1)

    def test_unknown_competition_is_rejected(self, sd):
        # When I ask for a competition that does not exist
        # Then a friendly error names the valid competitions
        with pytest.raises(q.QueryError, match="Unknown competition"):
            q.find_matches(sd, competition="premier league")


class TestLastMatchBetweenTwoTeams:
    """Scenario: When did Flamengo last play Corinthians?"""

    def test_last_match(self, sd):
        # When I ask for the last Flamengo vs Corinthians match
        match = q.last_match(sd, "Flamengo", opponent="Corinthians")
        # Then I receive the most recent one in the dataset
        all_between = q.find_matches(sd, team="Flamengo", opponent="Corinthians")
        assert match is not None
        assert match.date == max(m.date for m in all_between)
        # And the score is returned with it
        assert match.home_goal is not None and match.away_goal is not None
