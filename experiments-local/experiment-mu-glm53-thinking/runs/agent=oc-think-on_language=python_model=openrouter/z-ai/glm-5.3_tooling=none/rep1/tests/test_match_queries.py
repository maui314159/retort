"""Feature: Match Queries

BDD scenarios for the TASK.md examples:
- "Show me all Flamengo vs Fluminense matches"
- "What matches did Palmeiras play in 2023?"
- "Find all Copa do Brasil finals"
- "When did Flamengo last play Corinthians?"
"""

from __future__ import annotations

import pytest

from brazilian_soccer import queries as q
from brazilian_soccer.normalize import TeamResolutionError


class TestFindMatchesBetweenTwoTeams:
    """Feature: Match Queries - Scenario: Find matches between two teams."""

    def test_returns_matches_with_date_scores_and_competition(self, soccer):
        """Each match should have date, scores, and competition."""
        # Given the match data is loaded
        # When I search for matches between "Flamengo" and "Fluminense"
        result = q.search_matches(soccer, team="Flamengo", opponent="Fluminense")
        # Then I should receive a list of matches
        assert result["total_matches"] == 44
        assert result["matches"]
        for match in result["matches"]:
            # And each match should have date, scores, and competition
            assert match["date"] is not None
            assert match["home_goals"] is not None
            assert match["away_goals"] is not None
            assert match["competition"] in {
                "Brasileirão Série A",
                "Brasileirão Série B",
                "Brasileirão Série C",
                "Copa do Brasil",
                "Copa Libertadores",
            }
            # And only these two clubs appear
            assert {match["home"], match["away"]} == {"Flamengo", "Fluminense"}

    def test_head_to_head_record_and_latest_meeting(self, soccer):
        """Scenario: head-to-head summary with wins and latest match."""
        # Given the match data is loaded
        # When I ask for the Flamengo x Fluminense head-to-head
        result = q.head_to_head(soccer, "Flamengo", "Fluminense")
        # Then I get wins, draws and the latest match
        assert result["total_matches"] == 44
        assert result["record"]["Flamengo_wins"] == 18
        assert result["record"]["Fluminense_wins"] == 14
        assert result["record"]["draws"] == 12
        assert result["latest_match"]["date"] == "2023-11-11"
        assert result["latest_match"]["home_goals"] + result["latest_match"]["away_goals"] >= 0

    def test_competition_filter_applies_to_head_to_head(self, soccer):
        # Given the match data is loaded
        # When I restrict the head-to-head to the Brasileirão
        result = q.head_to_head(soccer, "Flamengo", "Fluminense", competition="Série A")
        # Then only league matches are counted
        assert result["total_matches"] == 42
        assert result["record"]["Flamengo_wins"] == 17

    def test_latest_meeting_between_two_specific_teams(self, soccer):
        """Scenario: 'When did Flamengo last play Corinthians?'"""
        # Given the match data is loaded
        # When I ask for the head-to-head
        result = q.head_to_head(soccer, "Flamengo", "Corinthians")
        # Then the latest match is the most recent date in the list
        dates = [m["date"] for m in result["matches"] if m["date"]]
        assert result["latest_match"]["date"] == max(dates)
        assert result["total_matches"] == 47


class TestFindMatchesByTeamAndSeason:
    """Feature: Match Queries - Scenario: matches by team and season."""

    def test_all_matches_for_a_team_in_a_season(self, soccer):
        """Scenario: 'What matches did Palmeiras play in 2023?'"""
        # Given the match data is loaded
        # When I search for Palmeiras matches in 2023
        result = q.search_matches(soccer, team="Palmeiras", season=2023)
        # Then I receive all of them across competitions
        assert result["total_matches"] == 43
        for match in result["matches"]:
            assert match["season"] == 2023
            assert "Palmeiras" in (match["home"], match["away"])

    def test_by_competition_and_season(self, soccer):
        # Given the match data is loaded
        # When I search Libertadores 2018 matches
        result = q.search_matches(soccer, competition="Libertadores", season=2018)
        # Then every match belongs to that competition and season
        assert result["total_matches"] == 126
        assert all(m["competition"] == "Copa Libertadores" for m in result["matches"])
        assert all(m["season"] == 2018 for m in result["matches"])

    def test_by_round(self, soccer):
        # Given the 2019 Brasileirão
        # When I ask for round 1 only
        result = q.search_matches(soccer, competition="Série A", season=2019, round=1)
        # Then a full round of 10 fixtures is returned
        assert result["total_matches"] == 10
        assert all(m["round"] == 1 for m in result["matches"])

    def test_by_date_range(self, soccer):
        # Given the match data is loaded
        # When I ask for Flamengo matches in September 2023
        result = q.search_matches(
            soccer, team="Flamengo", date_from="2023-09-01", date_to="2023-09-30"
        )
        # Then every match falls inside the window
        assert result["total_matches"] == 6
        for match in result["matches"]:
            assert "2023-09-01" <= match["date"] <= "2023-09-30"

    def test_by_libertadores_stage(self, soccer):
        """Scenario: 'Find all Copa Libertadores finals' (stage search)."""
        # Given Libertadores matches with stage labels
        # When I search for the 2019 'final' stage
        result = q.search_matches(
            soccer, competition="Libertadores", season=2019, stage="final"
        )
        # Then only the final itself is returned (not semifinals)
        assert result["total_matches"] == 1
        final = result["matches"][0]
        assert {final["home"], final["away"]} == {"Flamengo", "River Plate"}
        assert final["score"] == "2-1"

    def test_results_are_truncated_with_a_flag(self, soccer):
        # Given a query with many results
        # When I limit to 5
        result = q.search_matches(soccer, team="Flamengo", limit=5)
        # Then only 5 are returned and the response says so
        assert result["returned"] == 5
        assert result["truncated"] is True
        assert result["total_matches"] > 5

    def test_unplayed_fixtures_are_returned_without_scores(self, soccer):
        """Scenario: fixtures listed in 2022 with 'NA' scores."""
        # Given the 2022 Brasileirão contains unplayed listed fixtures
        # When I search Cuiabá's 2022 season
        result = q.search_matches(soccer, team="Cuiabá", season=2022, competition="Série A", limit=50)
        # Then the fixtures appear with score 'vs' and null goals
        assert result["total_matches"] == 38
        unplayed = [m for m in result["matches"] if m["score"] == "vs"]
        assert unplayed
        assert all(m["home_goals"] is None for m in unplayed)


class TestMatchSearchNameHandling:
    """Feature: Match Queries - team-name variations in search."""

    def test_any_spelling_of_a_team_finds_the_same_matches(self, soccer):
        # Given team names written in different conventions
        # When each is used to search
        by_suffix = q.search_matches(soccer, team="Palmeiras-SP", season=2022)
        by_bare = q.search_matches(soccer, team="Palmeiras", season=2022)
        by_full = q.search_matches(soccer, team="Sociedade Esportiva Palmeiras", season=2022)
        # Then all spellings return the same result set
        assert by_suffix["total_matches"] == by_bare["total_matches"] == by_full["total_matches"]

    def test_unknown_team_raises_a_helpful_error(self, soccer):
        # Given a misspelled team name
        # When I search
        # Then a resolution error suggests alternatives
        with pytest.raises(TeamResolutionError, match="Flamengoo"):
            q.search_matches(soccer, team="Flamengoo")

    def test_unknown_competition_raises_a_helpful_error(self, soccer):
        with pytest.raises(TeamResolutionError, match="not recognized"):
            q.search_matches(soccer, competition="Premier League")
