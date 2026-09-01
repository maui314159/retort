"""Feature: Match Queries
  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition
  (plus filtering by season, competition, date range, stage and source)
"""

import pytest

from brazilian_soccer import queries
from brazilian_soccer.queries import QueryError


class TestFindMatchesBetweenTwoTeams:
    def test_head_to_head_returns_dated_scored_matches(self, repo):
        # Given the match data is loaded
        # When I search for matches between "Flamengo" and "Fluminense"
        result = queries.head_to_head(repo, "Flamengo", "Fluminense")
        # Then I should receive a list of matches
        assert result["matches_played"] == 44
        assert result["matches"], "expected a non-empty match list"
        # And each match should have date, scores, and competition
        for match in result["matches"]:
            assert match["date"]
            assert isinstance(match["home_goals"], int)
            assert isinstance(match["away_goals"], int)
            assert match["competition"] in {
                "Brasileirão Serie A", "Copa do Brasil", "Copa Libertadores",
            }

    def test_head_to_head_teams_meet_on_both_sides(self, repo):
        # Given the Fla-Flu derby
        result = queries.head_to_head(repo, "Flamengo", "Fluminense")
        # When the matches are listed
        home_flamengo = any(
            m["home_team"] == "Flamengo" for m in result["matches"]
        )
        away_flamengo = any(
            m["away_team"] == "Flamengo" for m in result["matches"]
        )
        # Then Flamengo appears both at home and away across the fixture list
        assert home_flamengo and away_flamengo

    def test_most_recent_meeting_first(self, repo):
        # Given any two teams that played each other
        result = queries.head_to_head(repo, "Flamengo", "Corinthians", limit=5)
        # When matches are returned
        dates = [m["date"] for m in result["matches"]]
        # Then the most recent meeting comes first
        assert dates == sorted(dates, reverse=True)
        assert result["most_recent"]["date"] == dates[0]

    def test_when_did_flamengo_last_play_corinthians(self, repo):
        # Given the question "When did Flamengo last play Corinthians?"
        result = queries.head_to_head(repo, "Flamengo", "Corinthians")
        # Then the most recent meeting is returned with its score
        assert result["most_recent"]["date"] == "2023-10-08"
        assert result["most_recent"]["home_goals"] == 1
        assert result["most_recent"]["away_goals"] == 1


class TestMatchFilters:
    def test_matches_for_team_and_season(self, repo):
        # Given Palmeiras' 2023 season
        result = queries.search_matches(repo, team="Palmeiras", season=2023, limit=200)
        # When the matches are searched
        # Then only Palmeiras 2023 matches are returned
        assert result["total_matches"] == 43
        competitions = {m["competition"] for m in result["matches"]}
        # And they come from more than one competition/file (cross-file query)
        assert "Brasileirão Serie A" in competitions
        assert "Copa do Brasil" in competitions

    def test_matches_by_competition_alias(self, repo):
        # Given the competition alias "brasileirao"
        result = queries.search_matches(repo, competition="brasileirao", limit=5)
        # When matches are searched
        # Then only Serie A matches are returned
        assert all(m["competition"] == "Brasileirão Serie A" for m in result["matches"])
        assert result["total_matches"] > 8000

    def test_matches_by_date_range(self, repo):
        # Given May 2019
        result = queries.search_matches(
            repo,
            competition="Brasileirão Serie A",
            date_from="2019-05-01",
            date_to="2019-05-31",
            limit=200,
        )
        # When matches are searched
        # Then every match falls inside the date range
        assert result["total_matches"] == 50
        for match in result["matches"]:
            assert "2019-05-01" <= match["date"] <= "2019-05-31"

    def test_home_and_away_side_filters(self, repo):
        # Given Flamengo's 2019 Serie A campaign
        home = queries.search_matches(
            repo, home_team="Flamengo", season=2019, competition="serie a", limit=200
        )
        away = queries.search_matches(
            repo, away_team="Flamengo", season=2019, competition="serie a", limit=200
        )
        # When filtering by side
        # Then each side has its own fixtures and they do not overlap
        assert home["total_matches"] == 19
        assert away["total_matches"] == 19
        assert all(m["home_team"] == "Flamengo" for m in home["matches"])
        assert all(m["away_team"] == "Flamengo" for m in away["matches"])

    def test_venue_filter_rejects_unknown_values(self, repo):
        with pytest.raises(QueryError):
            queries.search_matches(repo, team="Flamengo", venue="middle")

    def test_opponent_filter(self, repo):
        # Given Palmeiras against Santos
        result = queries.search_matches(
            repo, team="Palmeiras", opponent="Santos", limit=200
        )
        # When the matches are searched
        # Then every match is exactly between those two teams
        assert result["total_matches"] > 10
        for match in result["matches"]:
            teams = {match["home_team"], match["away_team"]}
            assert teams == {"Palmeiras", "Santos"}


class TestStageAndRoundFilters:
    def test_libertadores_final_stage(self, repo):
        # Given the 2019 Copa Libertadores
        result = queries.search_matches(
            repo, competition="libertadores", season=2019, stage="final"
        )
        # When the final is requested
        # Then the famous single-match final is returned
        assert result["total_matches"] == 1
        final = result["matches"][0]
        assert final["home_team"] == "Flamengo"
        assert final["away_team"] == "River Plate"
        assert final["home_goals"] == 2
        assert final["away_goals"] == 1

    def test_libertadores_knockout_stage(self, repo):
        # Given the 2019 Copa Libertadores quarterfinals
        result = queries.search_matches(
            repo, competition="libertadores", season=2019, stage="quarterfinals"
        )
        # When the quarterfinals are requested
        # Then the eight two-legged ties are returned
        assert result["total_matches"] == 8

    def test_copa_do_brasil_finals(self, repo):
        # Given the 2019 Copa do Brasil
        result = queries.search_matches(
            repo, competition="copa do brasil", season=2019, stage="final"
        )
        # When the finals are requested
        # Then the two-legged final between Internacional and Athletico is found
        assert result["total_matches"] == 2
        finalists = set()
        for match in result["matches"]:
            finalists.add(match["home_team"])
            finalists.add(match["away_team"])
        assert finalists == {"Internacional", "Athletico Paranaense"}

    def test_cup_round_filter(self, repo):
        # Given Copa do Brasil round 1 in 2012
        result = queries.search_matches(
            repo, competition="copa do brasil", season=2012, round=1, limit=200
        )
        # When round 1 is requested
        # Then only first-round matches are returned
        assert result["total_matches"] > 20
        assert all(m["round"] == 1 for m in result["matches"])


class TestSearchBehaviour:
    def test_limit_and_truncation(self, repo):
        # Given a query with thousands of results
        result = queries.search_matches(repo, competition="serie a", limit=10)
        # When only ten are requested
        # Then ten are returned and truncation is signalled
        assert len(result["matches"]) == 10
        assert result["truncated"] is True
        assert result["total_matches"] > result["returned"]

    def test_sort_ascending(self, repo):
        # Given a request for oldest matches first
        result = queries.search_matches(
            repo, competition="serie a", limit=10, sort="date_asc"
        )
        dates = [m["date"] for m in result["matches"]]
        # When sorted ascending
        # Then the oldest Brasileirão match in the dataset comes first
        assert dates == sorted(dates)
        assert dates[0] == "2003-03-29"

    def test_raw_source_search_keeps_all_rows(self, repo):
        # Given the 2021 Serie A, over-recorded in the statistics file
        raw = queries.search_matches(
            repo,
            competition="serie a",
            season=2021,
            source="BR-Football-Dataset.csv",
            limit=200,
        )
        curated = queries.search_matches(repo, competition="serie a", season=2021, limit=200)
        # When searching the raw file instead of the curated view
        # Then the raw rows are returned even where duplicates were shadowed
        assert raw["total_matches"] == 491
        assert curated["total_matches"] == 380

    def test_unknown_competition_raises_helpful_error(self, repo):
        with pytest.raises(QueryError, match="Unknown competition"):
            queries.search_matches(repo, competition="Premier League")

    def test_unknown_team_raises_helpful_error(self, repo):
        with pytest.raises(QueryError, match="No team found"):
            queries.search_matches(repo, team="Bora Bora United")
