"""
BDD scenarios: match queries (TASK.md "Required Capabilities" #1).

Feature: Match Queries
  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition
"""

from __future__ import annotations

from datetime import date

import pytest

from brazilian_soccer_mcp.models import COPA_DO_BRASIL, LIBERTADORES


class TestFindMatchesBetweenTwoTeams:
    """Scenario: find matches between two teams (spec Gherkin example)."""

    def test_flamengo_vs_fluminense(self, service):
        # Given the match data is loaded
        # When I search for matches between "Flamengo" and "Fluminense"
        result = service.search_matches(team="Flamengo", opponent="Fluminense")
        # Then I should receive a list of matches
        assert result.total == 46
        assert len(result.matches) > 0
        # And each match should have date, scores, and competition
        for match in result.matches:
            assert match.date is not None
            assert match.home_goals is not None
            assert match.away_goals is not None
            assert match.competition

    def test_pairing_is_exactly_the_two_teams(self, service):
        result = service.search_matches(team="Flamengo", opponent="Fluminense")
        for match in result.matches:
            assert {match.home_id, match.away_id} == {"flamengo-rj", "fluminense-rj"}

    def test_order_does_not_matter(self, service):
        # Given the same two teams in reverse order
        reversed_result = service.search_matches(team="Fluminense", opponent="Flamengo")
        # When I compare with the original query
        # Then the same fixtures are found
        assert reversed_result.total == 46

    def test_results_are_chronological(self, service):
        result = service.search_matches(team="Flamengo", opponent="Fluminense", limit=100)
        dates = [m.date for m in result.matches]
        assert dates == sorted(dates)


class TestFindMatchesByTeam:
    """Scenario: 'What matches did Palmeiras play in 2023?'."""

    def test_palmeiras_2023(self, service):
        result = service.search_matches(team="Palmeiras", season=2023)
        # 2023 data comes from the BR-Football dataset (Série A + cups)
        assert result.total >= 40
        for match in result.matches:
            assert "palmeiras" in (match.home_id, match.away_id)

    def test_ignores_home_away_role(self, service):
        home = [m for m in service.search_matches(team="Palmeiras", season=2023, limit=200).matches
                if m.home_id == "palmeiras"]
        away = [m for m in service.search_matches(team="Palmeiras", season=2023, limit=200).matches
                if m.away_id == "palmeiras"]
        assert home and away


class TestFindMatchesByDateRange:
    """Scenario: 'What matches were played in September 2023?'."""

    def test_date_range_filter(self, service):
        result = service.search_matches(
            date_from="2023-09-01", date_to="2023-09-30", limit=200
        )
        assert result.total > 50
        for match in result.matches:
            assert date(2023, 9, 1) <= match.date <= date(2023, 9, 30)

    def test_invalid_date_is_rejected(self, service):
        with pytest.raises(ValueError):
            service.search_matches(date_from="Septiembre")


class TestFindMatchesByCompetitionAndStage:
    """Scenario: 'Find all Copa Libertadores semifinals of 2019'."""

    def test_stage_filter(self, service):
        result = service.search_matches(
            competition="libertadores", season=2019, stage="semifinals"
        )
        assert result.total == 4
        for match in result.matches:
            assert match.stage == "semifinals"
            assert match.competition == LIBERTADORES

    def test_competition_filter(self, service):
        result = service.search_matches(competition="Copa do Brasil", season=2019, limit=500)
        assert result.total > 100
        assert all(m.competition == COPA_DO_BRASIL for m in result.matches)

    def test_unknown_competition_rejected(self, service):
        with pytest.raises(ValueError):
            service.search_matches(competition="Premier League")


class TestFindFinals:
    """Scenario: 'Find all Copa do Brasil finals' / Libertadores finals."""

    def test_all_copa_do_brasil_finals(self, service):
        finals = service.finals("Copa do Brasil")
        # 12 seasons 2012-2023, each with a two-legged final
        assert len(finals) == 24
        seasons = {m.season for m in finals}
        assert seasons == set(range(2012, 2024))

    def test_all_libertadores_finals(self, service):
        finals = service.finals("Libertadores")
        # 2013-2018 two-legged, 2019-2020 single-match finals
        assert len(finals) == 14
        assert all(m.stage == "final" for m in finals)

    def test_leagues_have_no_finals(self, service):
        assert service.finals("brasileirao", 2019) == []

    def test_2019_libertadores_final_content(self, service):
        finals = service.finals("Libertadores", 2019)
        assert len(finals) == 1
        match = finals[0]
        assert match.home_display == "Flamengo"
        assert (match.home_goals, match.away_goals) == (2, 1)
        assert match.away_display == "River Plate"


class TestLastMatchBetweenTeams:
    """Scenario: 'When did Flamengo last play Corinthians?'."""

    def test_limit_one_returns_most_recent(self, service):
        result = service.search_matches(
            team="Flamengo", opponent="Corinthians", limit=1
        )
        assert result.total == 50
        match = result.matches[0]
        assert match.date == date(2023, 10, 8)
        assert match.home_display == "Corinthians"
        assert match.score_str() == "1-1"

    def test_historic_venue_is_kept(self, service):
        # Given the historical dataset records stadiums ('Arena' column)
        # When I search old matches
        # Then the venue is preserved
        result = service.search_matches(team="Vasco", season=2003, limit=100)
        with_venue = [m for m in result.matches if m.venue]
        assert with_venue, "expected at least one match with a recorded venue"


class TestFormatting:
    """Scenario: match listings render like TASK.md's example answers."""

    def test_match_line_format(self, service):
        from brazilian_soccer_mcp.formatting import format_match_line

        result = service.search_matches(team="Flamengo", opponent="Fluminense", limit=1)
        line = format_match_line(result.matches[0])
        # '- YYYY-MM-DD: Home X-Y Away (Competition ...)'
        assert line.startswith("- ")
        assert " - " not in line[2:12]  # date shape sanity
        assert "(" in line and ")" in line

    def test_listing_mentions_more_matches(self, service):
        from brazilian_soccer_mcp.formatting import format_match_search

        result = service.search_matches(team="Flamengo", opponent="Fluminense", limit=5)
        text = format_match_search(result)
        assert "more in dataset" in text
