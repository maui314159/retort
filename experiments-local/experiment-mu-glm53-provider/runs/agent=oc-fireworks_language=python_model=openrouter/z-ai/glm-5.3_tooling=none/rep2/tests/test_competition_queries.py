"""BDD scenarios for competition queries: standings, finals, champions.

Feature: Competition queries
  Scenario: Compute the 2019 Brasileirão table
    Given the match data is loaded
    When I request the 2019 Brasileirão standings
    Then Flamengo is champion with 90 points
    And the four relegated teams are marked
"""

from __future__ import annotations

import re


class TestLeagueStandings:
    def test_2019_brasileirao_table_matches_reference(self, svc):
        # Given the 2019 Serie A season (380 played matches)
        # When I compute the standings
        result = svc.league_standings(competition="Brasileirão", season=2019)
        # Then the table matches the specification's reference values
        assert "380 played matches" in result
        assert "1. Flamengo - 90 pts (28W, 6D, 4L" in result
        assert "Champion" in result
        assert "2. Santos - 74 pts" in result
        assert "3. Palmeiras - 74 pts" in result
        # And the relegated zone is marked
        assert result.count("Relegated") == 4

    def test_2019_relegated_teams(self, svc):
        # Given the 2019 bottom four
        # When I compute the standings
        result = svc.league_standings(season=2019)
        relegated = [
            ln for ln in result.splitlines() if "Relegated" in ln
        ]
        # Then Avaí is last and Cruzeiro went down
        assert "Avaí" in relegated[-1]
        assert "Cruzeiro" in relegated[0]

    def test_2020_relegated_teams(self, svc):
        # Given the 2020 season
        # When I compute the standings
        result = svc.league_standings(season=2020)
        relegated = " ".join(ln for ln in result.splitlines() if "Relegated" in ln)
        # Then Vasco, Goiás, Coritiba and Botafogo are relegated
        for team in ("Vasco", "Goiás", "Coritiba", "Botafogo"):
            assert team in relegated

    def test_2020_champion_is_flamengo(self, svc):
        # Given the 2020 season
        # When I compute the standings
        result = svc.league_standings(season=2020)
        # Then Flamengo is champion with 71 points
        assert "1. Flamengo - 71 pts" in result

    def test_default_season_is_the_latest(self, svc):
        # Given no season is specified
        # When I request the Brasileirão table
        result = svc.league_standings("Brasileirão")
        # Then the most recent season in the data is used
        assert "2023 standings" in result

    def test_home_and_away_tables_rank_venues(self, svc):
        # Given home advantage exists
        # When I compute the 2019 away-only table
        result = svc.league_standings(season=2019, venue="away")
        # Then it is labelled and no champion is crowned from away form
        assert "away matches only" in result
        assert "Champion" not in result
        assert "1. " in result

    def test_knockout_competitions_have_no_table(self, svc):
        # Given the Copa do Brasil is a knockout
        # When I request its standings
        result = svc.league_standings("Copa do Brasil")
        # Then the response explains and points to the finals tool
        assert "knockout" in result
        assert "finals" in result

    def test_unknown_season_lists_available_seasons(self, svc):
        # Given a season outside the data
        # When I request the standings
        result = svc.league_standings("Brasileirão", season=1996)
        # Then the available range is reported
        assert "available seasons" in result
        assert "2003-2023" in result

    def test_serie_b_table_is_computable(self, svc):
        # Given Serie B data from the extended file
        # When I compute the 2022 table
        result = svc.league_standings("Série B", season=2022)
        # Then a full 20-team table comes back (379 recorded matches after
        # dropping the file's one junk fixture)
        assert "379 played matches" in result
        assert len([ln for ln in result.splitlines() if re.match(r"\d+\. ", ln)]) == 20

    def test_competition_name_aliases(self, svc):
        # Given users say "serie a", "Serie A" or "Brasileirão"
        # When each is used
        # Then all resolve to the same competition
        for name in ("serie a", "Série A", "brasileirao", "Campeonato Brasileiro"):
            result = svc.league_standings(name, season=2019)
            assert "2019 standings" in result, name


class TestFinals:
    def test_libertadores_finals_list_all_seasons(self, svc):
        # Given Libertadores data covers 2013-2022
        # When I list the finals
        result = svc.finals("Libertadores")
        # Then every season appears with its deciding matches
        for season in range(2013, 2023):
            assert f"{season}:" in result, season

    def test_libertadores_winners(self, svc):
        # Given the finals data
        # When I list the finals
        result = svc.finals("Libertadores")
        # Then known champions are derived from the scores
        assert "Champion: Flamengo" in result          # 2019 (and 2022 note)
        assert "Champion: Grêmio" in result            # 2017
        assert "Champion: Palmeiras" in result         # 2020
        assert "Champion: River Plate" in result       # 2015 / 2018

    def test_level_aggregates_are_reported_honestly(self, svc):
        # Given some finals were decided on penalties
        # When I list Libertadores finals
        result = svc.finals("Libertadores")
        # Then the 2013 all-square final says penalties decided it
        assert "penalties" in result

    def test_missing_finals_carry_notes(self, svc):
        # Given 2021/2022 Libertadores finals are missing or scoreless
        # When I list the finals
        result = svc.finals("Libertadores")
        # Then curated notes explain what the dataset cannot express
        assert "2021 final is missing" in result
        assert "result not recorded" in result

    def test_copa_do_brasil_finals_and_champions(self, svc):
        # Given the Copa do Brasil finals 2012-2023
        # When I list them
        result = svc.finals("Copa do Brasil")
        # Then champions are derived from two-leg aggregates
        assert "Champion: Palmeiras" in result        # 2012, 2020
        assert "Champion: Flamengo" in result         # 2013
        assert "Champion: Atlético-MG" in result      # 2014, 2021
        assert "Champion: Grêmio" in result           # 2016
        assert "Champion: Cruzeiro" in result         # 2018
        assert "Champion: São Paulo" in result        # 2023
        # And the 2021-2023 finals note they were inferred
        assert result.count("inferred") >= 3

    def test_league_finals_point_to_standings(self, svc):
        # Given leagues have no finals
        # When I ask for Brasileirão finals
        result = svc.finals("Brasileirão")
        # Then the response points to the standings tool
        assert "league" in result and "league_standings" in result


class TestCompetitionInfo:
    def test_overview_lists_all_competitions(self, svc):
        # Given five competitions are loaded
        # When I request the overview
        result = svc.competition_info()
        # Then each competition shows match counts and season coverage
        for name in (
            "Brasileirão Serie A",
            "Brasileirão Serie B",
            "Brasileirão Serie C",
            "Copa do Brasil",
            "Copa Libertadores",
        ):
            assert name in result
            assert re.search(rf"{name}: \d+ matches", result)

    def test_brasileirao_statistics(self, svc):
        # Given all Serie A matches 2003-2023
        # When I request competition statistics
        result = svc.competition_info("Brasileirão")
        # Then goals and result rates are computed
        avg = float(re.search(r"Average goals per match: ([\d.]+)", result).group(1))
        assert 2.0 < avg < 3.0
        home = float(re.search(r"Home wins: \d+ \(([\d.]+)%\)", result).group(1))
        away = float(re.search(r"Away wins: \d+ \(([\d.]+)%\)", result).group(1))
        assert home > away  # home advantage holds across 20 years

    def test_season_comparison_2018_vs_2019(self, svc):
        # Given two seasons
        # When I request info for each
        info_2018 = svc.competition_info("Brasileirão", season=2018)
        info_2019 = svc.competition_info("Brasileirão", season=2019)
        # Then both report complete seasons with comparable statistics
        assert "Matches played: 380 of 380" in info_2018
        assert "Matches played: 380 of 380" in info_2019
        avg_18 = float(re.search(r"Average goals per match: ([\d.]+)", info_2018).group(1))
        avg_19 = float(re.search(r"Average goals per match: ([\d.]+)", info_2019).group(1))
        assert 2.0 < avg_18 < 3.0 and 2.0 < avg_19 < 3.0
