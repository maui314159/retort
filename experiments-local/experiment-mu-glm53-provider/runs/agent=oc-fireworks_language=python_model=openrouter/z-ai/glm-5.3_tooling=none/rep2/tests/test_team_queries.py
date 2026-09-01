"""BDD scenarios for team queries.

Feature: Team queries
  Scenario: Get team statistics
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season "2023"
    Then I should receive wins, losses, draws, and goals
"""

from __future__ import annotations

import re


class TestTeamStats:
    def test_corinthians_home_record_2022(self, svc):
        # Given the match data is loaded
        # When I request Corinthians' home record for the 2022 Brasileirão
        result = svc.team_stats(
            "Corinthians", season=2022, competition="Brasileirão", venue="home"
        )
        # Then I receive 19 home matches with consistent W/D/L and goals
        assert "Matches: 19" in result
        wins = int(re.search(r"Wins: (\d+)", result).group(1))
        draws = int(re.search(r"Draws: (\d+)", result).group(1))
        losses = int(re.search(r"Losses: (\d+)", result).group(1))
        assert wins + draws + losses == 19
        assert "Win rate:" in result
        assert "Goals For:" in result and "Goals Against:" in result

    def test_stats_across_all_competitions_by_default(self, svc):
        # Given a team plays league and cups in one season
        # When I request season stats without a competition filter
        only_league = svc.team_stats("Corinthians", season=2022, competition="Brasileirão")
        everything = svc.team_stats("Corinthians", season=2022)
        league_matches = int(re.search(r"Matches: (\d+)", only_league).group(1))
        all_matches = int(re.search(r"Matches: (\d+)", everything).group(1))
        # Then the unfiltered count includes cup matches too
        assert all_matches > league_matches

    def test_away_venue_filter(self, svc):
        # Given home and away records differ
        # When I request only league home/away matches
        home = svc.team_stats("Flamengo", season=2019, competition="Brasileirão", venue="home")
        away = svc.team_stats("Flamengo", season=2019, competition="Brasileirão", venue="away")
        # Then both show exactly half a league season
        assert "Matches: 19" in home
        assert "Matches: 19" in away

    def test_unknown_season_returns_no_matches_message(self, svc):
        # Given a season with no data
        # When I request stats
        # Then a graceful message comes back
        result = svc.team_stats("Palmeiras", season=1999)
        assert "no played matches" in result

    def test_name_variants_give_the_same_answer(self, svc):
        # Given team name variations from the spec
        # When each is used for stats
        # Then they all resolve to the same team
        a = svc.team_stats("Palmeiras-SP", season=2019)
        b = svc.team_stats("Palmeiras", season=2019)
        c = svc.team_stats("PALMEIRAS sp", season=2019)
        assert a == b == c


class TestTeamProfile:
    def test_profile_lists_competitions_and_seasons(self, svc):
        # Given Palmeiras appears in three competitions
        # When I request its profile
        result = svc.team_profile("Palmeiras")
        # Then every competition and the all-time record appear
        assert "Brasileirão Serie A" in result
        assert "Copa do Brasil" in result
        assert "Copa Libertadores" in result
        assert "All-time record:" in result
        assert "Biggest win in dataset:" in result

    def test_profile_of_unlicensed_club_notes_fifa_gap(self, svc):
        # Given Flamengo is absent from the FIFA dataset
        # When I request its profile
        result = svc.team_profile("Flamengo")
        # Then the licensing limitation is explained
        assert "FIFA dataset: no players recorded" in result
        assert "licensing" in result

    def test_profile_of_licensed_club_shows_squad(self, svc):
        # Given Grêmio has 20 players in the FIFA dataset
        # When I request its profile
        result = svc.team_profile("Grêmio")
        # Then the squad summary appears
        assert re.search(r"FIFA dataset: \d+ players, average rating", result)


class TestTeamResolutionErrors:
    def test_unknown_team_returns_suggestions(self, svc):
        # Given a team that does not exist anywhere in the data
        # When I request stats
        # Then helpful suggestions come back
        result = svc.team_stats("Manchester United")
        assert "not found" in result

    def test_ambiguous_team_lists_candidates(self, svc):
        # Given an ambiguous bare name
        # When I request stats
        # Then the possible clubs are listed
        result = svc.team_stats("Atletico")
        assert "ambiguous" in result
        assert "Atlético-MG" in result
