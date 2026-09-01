"""
Feature: Match Queries
  As a soccer fan asking an LLM about Brazilian soccer
  I want to find fixtures by team, opponent, competition, season, stage
  and date range
  So that every match answer shows date, score and competition.
"""

from __future__ import annotations

import collections

from brazilian_soccer_mcp.queries import (
    last_match_between,
    search_matches,
)


class TestFindMatchesBetweenTeams:
    """TASK.md: "Show me all Flamengo vs Fluminense matches"."""

    def test_find_matches_between_two_teams(self, ds):
        """
        Scenario: Find matches between two teams
          Given the match data is loaded
          When I search for matches between "Flamengo" and "Fluminense"
          Then I should receive a list of matches
          And each match should have date, scores, and competition
        """
        result = search_matches(ds, team="Flamengo", opponent="Fluminense")
        assert result["ok"], result
        assert result["team"] == "Flamengo"
        assert result["opponent"] == "Fluminense"
        assert result["total"] == 44
        assert result["shown"] == 20  # default limit
        assert result["truncated"] is True
        for match in result["matches"]:
            assert match["date"]
            assert match["score"]
            assert match["competition_display"]
            assert {match["home"], match["away"]} == {"Flamengo", "Fluminense"}

    def test_matches_are_newest_first(self, ds):
        """
        Scenario: results are sorted most-recent-first
          Given the match data is loaded
          When I search Flamengo vs Fluminense matches
          Then the first result is newer than the last
        """
        result = search_matches(ds, team="Flamengo", opponent="Fluminense", limit=200)
        dates = [m["date"] for m in result["matches"] if m["date"]]
        assert dates == sorted(dates, reverse=True)

    def test_team_name_spelling_is_forgiving(self, ds):
        """
        Scenario: any spelling of the team works
          Given the match data is loaded
          When I search "Flamengo-RJ" vs "Fluminense-RJ"
          Then I get the same fixtures as "Flamengo" vs "Fluminense"
        """
        result = search_matches(ds, team="Flamengo-RJ", opponent="Fluminense-RJ")
        assert result["ok"]
        assert result["total"] == 44

    def test_unknown_team_is_reported_with_suggestions(self, ds):
        """
        Scenario: an unknown team yields a helpful error
          Given the match data is loaded
          When I search for "Flamengoo"
          Then the result is an error suggesting the right club
        """
        result = search_matches(ds, team="Flamengoo")
        assert not result["ok"]
        assert "Flamengo" in result["error"]


class TestSearchBySeasonCompetitionDate:
    """TASK.md: "What matches did Palmeiras play in 2023?"."""

    def test_matches_by_team_and_season(self, ds):
        """
        Scenario: a team's fixtures in one season across competitions
          Given the match data is loaded
          When I search Palmeiras matches for season 2023
          Then I receive 43 fixtures
          And they span Série A and the Copa do Brasil
        """
        result = search_matches(ds, team="Palmeiras", season=2023, limit=200)
        assert result["ok"]
        assert result["total"] == 43
        per_comp = collections.Counter(m["competition"] for m in result["matches"])
        assert per_comp["serie_a"] == 37
        assert per_comp["copa_do_brasil"] == 6

    def test_filter_by_competition(self, ds):
        """
        Scenario: restrict to one competition
          Given the match data is loaded
          When I search Palmeiras 2023 matches in the Copa do Brasil
          Then only cup fixtures are returned
        """
        result = search_matches(
            ds, team="Palmeiras", season=2023, competition="Copa do Brasil", limit=200
        )
        assert result["ok"]
        assert result["total"] == 6
        assert all(m["competition"] == "copa_do_brasil" for m in result["matches"])

    def test_filter_by_date_range(self, ds):
        """
        Scenario: date-range filtering
          Given the match data is loaded
          When I search Palmeiras matches in June 2023
          Then every result falls inside the range
        """
        result = search_matches(
            ds,
            team="Palmeiras",
            date_from="2023-06-01",
            date_to="2023-06-30",
            limit=200,
        )
        assert result["ok"]
        assert result["total"] == 4
        assert all("2023-06" in m["date"] for m in result["matches"])

    def test_filter_by_round(self, ds):
        """
        Scenario: numeric round filtering
          Given the match data is loaded
          When I search Série A 2019 round 25
          Then exactly ten fixtures are returned
        """
        result = search_matches(
            ds, competition="serie_a", season=2019, stage="25", limit=100
        )
        assert result["ok"]
        assert result["total"] == 10
        assert all(m["round"] == "25" for m in result["matches"])

    def test_invalid_competition_lists_valid_ones(self, ds):
        """
        Scenario: an unknown competition is rejected with guidance
          Given the match data is loaded
          When I search with competition "Premier League"
          Then the error lists the valid competitions
        """
        result = search_matches(ds, competition="Premier League")
        assert not result["ok"]
        assert "serie_a" in result["valid_competitions"]

    def test_libertadores_needs_stage_names_not_rounds(self, ds):
        """
        Scenario: Libertadores is filtered by stage names
          Given the match data is loaded
          When I search Libertadores with a numeric round
          Then the error explains the stage vocabulary
        """
        result = search_matches(ds, competition="libertadores", stage="5")
        assert not result["ok"]
        assert "stage" in result["error"].lower()


class TestFinalsAndStages:
    """TASK.md: "Find all Copa do Brasil finals"."""

    def test_copa_do_brasil_finals(self, ds):
        """
        Scenario: every completed cup season has a two-legged final
          Given the match data is loaded
          When I search Copa do Brasil stage "final"
          Then seasons 2012-2020 each contribute exactly two matches
          And 2021 contributes none (the dataset ends mid-tournament)
        """
        result = search_matches(
            ds, competition="copa_do_brasil", stage="final", limit=100
        )
        assert result["ok"]
        per_season = collections.Counter(m["season"] for m in result["matches"])
        for season in range(2012, 2021):
            assert per_season[season] == 2, season
        assert per_season.get(2021, 0) == 0

    def test_copa_final_2019_teams(self, ds):
        """
        Scenario: the 2019 cup final is Athletico Paranaense vs Internacional
          Given the match data is loaded
          When I search Copa do Brasil 2019 finals
          Then both legs pair those two clubs
        """
        result = search_matches(
            ds, competition="copa_do_brasil", season=2019, stage="final"
        )
        assert result["ok"] and result["total"] == 2
        for match in result["matches"]:
            assert {match["home"], match["away"]} == {
                "Athletico Paranaense",
                "Internacional",
            }

    def test_libertadores_finals(self, ds):
        """
        Scenario: Libertadores finals are identifiable by stage
          Given the match data is loaded
          When I search Libertadores stage "final"
          Then the 2019 final is Flamengo 2-1 River Plate
          And the 2020 final is Palmeiras 1-0 Santos
          And one unplayed final (season unknown) is listed without a score
        """
        result = search_matches(
            ds, competition="libertadores", stage="final", limit=100
        )
        assert result["ok"]
        by_season = collections.defaultdict(list)
        for match in result["matches"]:
            by_season[match["season"]].append(match)
        flamengo_win = [m for m in by_season[2019] if m["home"] == "Flamengo"]
        assert flamengo_win and flamengo_win[0]["score"] == "2-1"
        palmeiras_win = [m for m in by_season[2020] if m["home"] == "Palmeiras"]
        assert palmeiras_win and palmeiras_win[0]["score"] == "1-0"
        unplayed = [m for m in result["matches"] if m["season"] is None]
        assert unplayed and unplayed[0]["score"] == "not played"

    def test_libertadores_stage_aliases(self, ds):
        """
        Scenario: stage names are forgiving
          Given the match data is loaded
          When I search Libertadores "semi-finals" and "semifinals"
          Then both return the same matches
        """
        loose = search_matches(
            ds, competition="libertadores", stage="semi-finals", limit=200
        )
        strict = search_matches(
            ds, competition="libertadores", stage="semifinals", limit=200
        )
        assert loose["ok"] and strict["ok"]
        assert loose["total"] == strict["total"] > 20


class TestLastMatch:
    """TASK.md: "When did Flamengo last play Corinthians? What was the score?"."""

    def test_last_match_between(self, ds):
        """
        Scenario: the most recent meeting of two clubs
          Given the match data is loaded
          When I ask for the last match between Flamengo and Corinthians
          Then I receive the newest played fixture with its score
        """
        result = last_match_between(ds, "Flamengo", "Corinthians")
        assert result["ok"], result
        latest = result["last_played"]
        assert latest["date"] == "2023-10-08"
        assert latest["score"] == "1-1"
        assert {latest["home"], latest["away"]} == {"Corinthians", "Flamengo"}
        assert result["total_meetings"] == 48

    def test_last_match_pair_without_history(self, ds):
        """
        Scenario: two clubs that never met
          Given the match data is loaded
          When I ask for the last match between Flamengo and Sampaio Corrêa
          Then the result explains there is no such fixture
        """
        result = last_match_between(ds, "Flamengo", "Sampaio Corrêa")
        assert not result["ok"]
        assert "no matches" in result["error"].lower()
