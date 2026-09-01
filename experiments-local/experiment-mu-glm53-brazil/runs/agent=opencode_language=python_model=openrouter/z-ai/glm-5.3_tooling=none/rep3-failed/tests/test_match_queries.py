"""BDD scenarios for match queries.

Feature: Match Queries
  Users ask for matches by team, opponent, competition, season, date
  range and stage.  Results must include date, score and competition.
"""

from __future__ import annotations

from datetime import date

from brazilian_soccer_mcp.queries import QueryError


class TestFindMatchesBetweenTwoTeams:
    """
    Scenario: Find matches between two teams
      Given the match data is loaded
      When I search for matches between "Flamengo" and "Fluminense"
      Then I should receive a list of matches
      And each match should have date, scores, and competition
    """

    def test_when_searching_fla_flu_then_each_match_has_date_scores_and_competition(self, engine):
        result = engine.search_matches(team="Flamengo", opponent="Fluminense", limit=200)
        assert result.total >= 40
        assert result.matches
        for match in result.matches:
            assert match.date is not None
            assert match.competition
            assert match.home_display and match.away_display

    def test_when_searching_fla_flu_then_both_home_away_orders_appear(self, engine):
        result = engine.search_matches(team="Flamengo", opponent="Fluminense", limit=200)
        home_flamengo = any(m.home_key == "flamengo-rj" for m in result.matches)
        away_flamengo = any(m.away_key == "flamengo-rj" for m in result.matches)
        assert home_flamengo and away_flamengo

    def test_when_searching_fla_flu_then_results_are_ordered_most_recent_first(self, engine):
        result = engine.search_matches(team="Flamengo", opponent="Fluminense", limit=200)
        dates = [m.date for m in result.matches if m.date]
        assert dates == sorted(dates, reverse=True)


class TestFindMatchesByTeamAndSeason:
    """
    Scenario: What matches did Palmeiras play in 2023?
      Given the match data is loaded
      When I search for Palmeiras matches in season 2023
      Then every returned match is from 2023 and involves Palmeiras
    """

    def test_when_searching_palmeiras_2023_then_all_matches_are_palmeiras_2023(self, engine):
        result = engine.search_matches(team="Palmeiras", season=2023, limit=200)
        assert result.total >= 30
        for match in result.matches:
            assert match.season == 2023
            assert "palmeiras" in (match.home_key, match.away_key)

    def test_when_searching_without_a_team_then_all_teams_are_returned(self, engine):
        result = engine.search_matches(season=2019, competition="Série A", limit=500)
        assert result.total == 380


class TestFindMatchesByDateRange:
    """
    Scenario: Find matches within a date range
      Given the match data is loaded
      When I search for matches between 2019-09-01 and 2019-10-01
      Then every returned match falls inside the range
    """

    def test_when_filtering_by_date_range_then_all_matches_are_within_range(self, engine):
        result = engine.search_matches(
            date_from="2019-09-01", date_to="2019-10-01", limit=500
        )
        assert result.total > 50
        for match in result.matches:
            assert date(2019, 9, 1) <= match.date <= date(2019, 10, 1)

    def test_when_a_date_is_badly_formatted_then_a_helpful_error_is_raised(self, engine):
        try:
            engine.search_matches(date_from="tomorrow")
        except QueryError as error:
            assert "date_from" in str(error)
        else:
            raise AssertionError("expected QueryError for invalid date")


class TestFindMatchesByCompetitionAndStage:
    """
    Scenario: Find the Copa Libertadores final
      Given the Libertadores data is loaded
      When I search for stage "final" in season 2019
      Then I find Flamengo 2-1 River Plate
    """

    def test_when_searching_the_2019_libertadores_final_then_flamengo_beat_river_plate(self, engine):
        result = engine.search_matches(competition="Libertadores", season=2019, stage="final")
        finals = result.matches
        assert any(
            m.home_key == "flamengo-rj"
            and m.away_goals is not None
            and m.home_goals == 2
            and m.away_goals == 1
            and m.away_display == "River Plate"
            for m in finals
        )

    def test_when_searching_the_2020_libertadores_final_then_palmeiras_beat_santos(self, engine):
        result = engine.search_matches(competition="Libertadores", season=2020, stage="final")
        assert any(
            m.home_key == "palmeiras" and m.home_goals == 1 and m.away_goals == 0
            for m in result.matches
        )

    def test_when_searching_copa_do_brasil_finals_then_two_legged_finals_are_found(self, engine):
        result = engine.search_matches(competition="Copa do Brasil", stage="final", limit=50)
        assert result.total >= 18
        seasons = {m.season for m in result.matches}
        assert 2015 in seasons
        finalists_2015 = {
            m.home_display for m in result.matches if m.season == 2015
        } | {m.away_display for m in result.matches if m.season == 2015}
        assert {"Santos - SP", "Palmeiras - SP"} <= finalists_2015

    def test_when_searching_group_stage_matches_then_only_group_matches_returned(self, engine):
        result = engine.search_matches(
            competition="Libertadores", season=2019, stage="group", limit=500
        )
        assert result.total > 50
        assert all(m.stage == "group stage" for m in result.matches)


class TestUnplayedMatches:
    """
    Scenario: Matches without scores are listed but excluded from statistics
      Given the Brasileirão data contains unplayed fixtures
      When I search all sources for Cuiabá in 2022
      Then some matches have no score
    """

    def test_when_searching_all_sources_for_cuiaba_2022_then_unplayed_matches_have_no_score(self, engine):
        result = engine.search_matches(team="Cuiabá", season=2022, all_sources=True, limit=100)
        unplayed = [m for m in result.matches if not m.played]
        assert unplayed
        for match in unplayed:
            assert match.home_goals is None
            assert match.away_goals is None


class TestVenueFilter:
    """
    Scenario: Filter a team's matches by venue
      Given the match data is loaded
      When I search Palmeiras home matches in 2023
      Then Palmeiras is always the home side
    """

    def test_when_filtering_home_matches_then_the_team_is_always_home(self, engine):
        result = engine.search_matches(team="Palmeiras", season=2023, venue="home", limit=100)
        assert result.matches
        assert all(m.home_key == "palmeiras" for m in result.matches)

    def test_when_filtering_away_matches_then_the_team_is_always_away(self, engine):
        result = engine.search_matches(team="Palmeiras", season=2023, venue="away", limit=100)
        assert result.matches
        assert all(m.away_key == "palmeiras" for m in result.matches)
