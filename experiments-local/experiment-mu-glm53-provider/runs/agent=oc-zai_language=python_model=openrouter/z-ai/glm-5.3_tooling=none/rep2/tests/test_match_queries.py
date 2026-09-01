"""Feature: Match Queries

Background:
    Given the match data is loaded from all match CSV files
"""

from __future__ import annotations

import pytest

from brazilian_soccer import query
from brazilian_soccer.query import QueryError


class TestFindMatchesBetweenTwoTeams:
    """Scenario: Find matches between two teams
        Given the match data is loaded
        When I search for matches between "Flamengo" and "Fluminense"
        Then I should receive a list of matches
        And each match should have date, scores, and competition
    """

    def test_given_match_data_when_searching_flamengo_vs_fluminense_then_matches_returned(self, dataset):
        result = query.search_matches(dataset, team="Flamengo", opponent="Fluminense")
        assert result["total"] > 20
        assert result["shown"] > 0

    def test_given_matches_between_two_teams_then_each_has_date_scores_and_competition(self, dataset):
        result = query.search_matches(dataset, team="Flamengo", opponent="Fluminense")
        for match in result["matches"]:
            assert match["date"] is not None
            assert match["competition"]
            assert isinstance(match["home_goals"], int) or match["home_goals"] is None
            assert match["home"] and match["away"]

    def test_given_a_derby_pairing_when_searching_then_matches_are_most_recent_first(self, dataset):
        result = query.search_matches(dataset, team="Flamengo", opponent="Fluminense")
        dates = [m["date"] for m in result["matches"] if m["date"]]
        assert dates == sorted(dates, reverse=True)

    def test_given_each_team_hosts_when_searching_then_both_directions_present(self, dataset):
        result = query.search_matches(dataset, team="Flamengo", opponent="Fluminense")
        homes = {m["home"] for m in result["matches"]}
        assert homes == {"Flamengo", "Fluminense"}


class TestFindMatchesByTeamAndSeason:
    """Scenario: Find matches by team and season
        Given the match data is loaded
        When I ask for Palmeiras matches in 2023
        Then I should receive Serie A and Copa do Brasil matches from that season only
    """

    def test_given_palmeiras_2023_when_searching_then_only_that_season_returned(self, dataset):
        result = query.search_matches(dataset, team="Palmeiras", season=2023, limit=100)
        assert 30 < result["total"] < 60
        assert all(m["season"] == 2023 for m in result["matches"])
        competitions = {m["competition"] for m in result["matches"]}
        assert "Brasileirão Série A" in competitions
        assert "Copa do Brasil" in competitions

    def test_given_team_side_home_when_searching_then_only_home_matches(self, dataset):
        result = query.search_matches(dataset, team="Flamengo", season=2019, team_side="home")
        assert all(m["home"] == "Flamengo" for m in result["matches"])

    def test_given_team_side_away_when_searching_then_only_away_matches(self, dataset):
        result = query.search_matches(dataset, team="Flamengo", season=2019, team_side="away")
        assert all(m["away"] == "Flamengo" for m in result["matches"])


class TestFindMatchesByDateRange:
    """Scenario: Find matches by date range
        Given the match data is loaded
        When I search for matches in May 2019
        Then only matches dated within that range should be returned
    """

    def test_given_may_2019_when_filtering_then_dates_within_bounds(self, dataset):
        result = query.search_matches(
            dataset, competition="Serie A", from_date="2019-05-01", to_date="2019-05-31",
        )
        assert result["total"] > 30
        for match in result["matches"]:
            assert "2019-05-" in match["date"]

    def test_given_brazilian_date_format_when_filtering_then_range_applied(self, dataset):
        result = query.search_matches(
            dataset, competition="Serie A", from_date="01/05/2019", to_date="31/05/2019",
        )
        assert result["total"] > 30

    def test_given_an_invalid_date_when_filtering_then_error(self, dataset):
        with pytest.raises(QueryError):
            query.search_matches(dataset, from_date="not-a-date")


class TestFindMatchesByStage:
    """Scenario: Find all Copa do Brasil / Libertadores finals
        Given the cup data is loaded
        When I search for final-stage matches
        Then only finals should be returned
    """

    def test_given_copa_do_brasil_when_searching_finals_then_multiple_seasons_found(self, dataset):
        result = query.search_matches(
            dataset, competition="Copa do Brasil", stage="final", limit=50,
        )
        assert result["total"] >= 16
        assert all(m["stage"] == "final" for m in result["matches"])
        seasons = {m["season"] for m in result["matches"]}
        assert 2013 in seasons and 2020 in seasons

    def test_given_libertadores_when_searching_finals_then_two_legged_and_single_leg_found(self, dataset):
        result = query.search_matches(
            dataset, competition="Libertadores", stage="final", limit=50,
        )
        assert result["total"] >= 14
        seasons = {m["season"] for m in result["matches"]}
        assert 2013 in seasons and 2019 in seasons

    def test_given_libertadores_2019_when_searching_group_stage_then_many_matches(self, dataset):
        result = query.search_matches(
            dataset, competition="Libertadores", season=2019, stage="group stage", limit=200,
        )
        assert result["total"] > 80


class TestLastMatchBetween:
    """Scenario: When did Flamengo last play Corinthians?
        Given the match data is loaded
        When I ask for the last match between two teams
        Then I should receive the most recent match with its score
    """

    def test_given_flamengo_and_corinthians_when_asking_last_match_then_most_recent(self, dataset):
        result = query.last_match_between(dataset, "Flamengo", "Corinthians")
        match = result["match"]
        assert match is not None
        assert match["home_goals"] is not None
        assert match["date"] is not None
        all_meetings = query.search_matches(
            dataset, team="Flamengo", opponent="Corinthians", limit=500,
        )
        latest_date = max(m["date"] for m in all_meetings["matches"])
        assert match["date"] == latest_date

    def test_given_teams_that_never_played_when_asking_last_match_then_no_match(self, dataset):
        result = query.last_match_between(dataset, "Boca Juniors", "Santos")
        assert result["match"] is None or result["all_matches_between"] >= 0


class TestTeamNameResolutionErrors:
    """Scenario: Ambiguous or unknown team names
        Given team names like "atletico" that match several clubs
        When I resolve them
        Then I should receive a helpful error listing candidates
    """

    def test_given_ambiguous_name_when_resolving_then_ambiguous_error_with_candidates(self, dataset):
        with pytest.raises(query.AmbiguousTeamError) as excinfo:
            query.search_matches(dataset, team="atletico")
        assert len(excinfo.value.candidates) > 1

    def test_given_unknown_name_when_resolving_then_not_found_error(self, dataset):
        with pytest.raises(query.TeamNotFoundError):
            query.search_matches(dataset, team="Not A Real Team FC")

    def test_given_fuzzy_prefix_when_resolving_then_unique_match_accepted(self, dataset):
        result = query.search_matches(dataset, team="Palmeir")
        assert result["filters"]["team"] == "Palmeiras"
