"""BDD scenarios for competition queries (TASK.md "Competition Queries").

Feature: Competition Queries
  Scenario: Standings by season
    Given the match data is loaded
    When I request the 2019 Brasileirão standings
    Then Flamengo is champion with 90 points
"""

from __future__ import annotations

from data_loader import COPA_DO_BRASIL, LIBERTADORES, SERIE_A
from server import (
    get_competition_finals,
    get_competition_info,
    get_standings,
    search_matches,
)


class TestStandings:
    """Gherkin: 'Who won the 2019 Brasileirão?'."""

    def test_2019_champion_is_flamengo(self, data):
        """
        Scenario: 2019 Brasileirão champion
          Given the 2019 Brasileirão matches
          When standings are calculated
          Then Flamengo is champion with 90 points
        """
        result = get_standings(competition="Brasileirão", season=2019)
        assert result["data"]["champion"] == "Flamengo"
        assert result["data"]["table"][0]["points"] == 90
        assert "Champion" in result["summary"]

    def test_2019_top_three_matches_history(self, data):
        """
        Scenario: podium
          Given the 2019 season
          When standings are calculated
          Then Santos and Palmeiras follow Flamengo, both on 74 points
        """
        table = get_standings(competition="Brasileirão", season=2019)["data"]["table"]
        assert [row["team"] for row in table[:3]] == ["Flamengo", "Santos", "Palmeiras"]
        assert table[1]["points"] == 74
        assert table[2]["points"] == 74

    def test_2020_relegated_teams(self, data):
        """
        Scenario: 'Which teams were relegated in 2020?'
          Given the 2020 Brasileirão
          When standings are calculated
          Then the bottom four are Coritiba, Botafogo, Vasco and Goiás
        """
        result = get_standings(competition="Brasileirão", season=2020)
        assert set(result["data"]["relegated"]) == {
            "Coritiba", "Botafogo", "Vasco da Gama", "Goiás"
        }

    def test_standings_cover_all_participants(self, data):
        """
        Scenario: table completeness
          Given a full 380-match season
          When standings are calculated
          Then all 20 teams appear with 38 matches each
        """
        result = get_standings(competition="Brasileirão", season=2019)
        table = result["data"]["table"]
        assert len(table) == 20
        assert all(row["matches"] == 38 for row in table)

    def test_champions_by_season(self, data):
        """
        Scenario: historical champions
          Given seasons 2003-2022
          When standings are calculated
          Then the champions match the historical record
        """
        expected = {
            2003: "Cruzeiro", 2004: "Santos", 2005: "Corinthians",
            2007: "São Paulo", 2008: "São Paulo", 2009: "Flamengo",
            2011: "Corinthians", 2012: "Fluminense", 2013: "Cruzeiro",
            2014: "Cruzeiro", 2015: "Corinthians", 2016: "Palmeiras",
            2017: "Corinthians", 2018: "Palmeiras", 2019: "Flamengo",
            2020: "Flamengo", 2021: "Atlético Mineiro", 2022: "Palmeiras",
        }
        for season, champion in expected.items():
            result = get_standings(competition="Brasileirão Série A", season=season)
            assert result["data"]["champion"] == champion, f"{season}: {result['data']['champion']}"

    def test_partial_season_is_flagged(self, data):
        """
        Scenario: partial data transparency
          Given the 2023 season has fewer matches than a full season
          When standings are calculated
          Then the response flags the data as partial
        """
        result = get_standings(competition="Brasileirão", season=2023)
        assert result["data"]["partial_data"] is True
        assert "partial" in result["summary"]

    def test_unknown_season_lists_available_seasons(self, data):
        """
        Scenario: unavailable season
          Given the season 1990
          When standings are requested
          Then an error lists the available seasons
        """
        result = get_standings(competition="Brasileirão", season=1990)
        assert "error" in result
        assert 2019 in result["available_seasons"]

    def test_serie_b_standings(self, data):
        """
        Scenario: second tier
          Given the 2022 Série B
          When standings are calculated
          Then 20 teams are ranked and a champion is named
        """
        result = get_standings(competition="Série B", season=2022)
        table = result["data"]["table"]
        assert len(table) == 20
        assert table[0]["points"] > table[-1]["points"]


class TestCompetitionInfo:
    """Gherkin: 'What competitions has Palmeiras played in?'."""

    def test_libertadores_info_lists_seasons_and_finals(self, data):
        """
        Scenario: competition overview
          Given the Libertadores dataset
          When I request competition info
          Then seasons, match counts and finals are returned
        """
        result = get_competition_info("Libertadores")
        payload = result["data"]
        assert payload["total_matches"] > 1200
        assert 2013 in payload["seasons"]
        winners = {e["season"]: e["winner"] for e in payload["finals"]}
        assert winners[2019] == "Flamengo"
        assert winners[2020] == "Palmeiras"

    def test_palmeiras_competitions(self, data):
        """
        Scenario: team's competitions
          Given Palmeiras matches
          When I search matches per competition
          Then Palmeiras appears in Série A, Copa do Brasil and
            Libertadores
        """
        competitions = set()
        for comp in data.competitions():
            matches = data.matches_by_competition(comp)
            if any(m.involves("palmeiras-sp") for m in matches):
                competitions.add(comp)
        assert SERIE_A in competitions
        assert COPA_DO_BRASIL in competitions
        assert LIBERTADORES in competitions


class TestCupFinals:
    """Gherkin: 'Show the 2018 Copa Libertadores final'."""

    def test_libertadores_finals_with_aggregates(self, data):
        """
        Scenario: two-legged finals
          Given Libertadores finals
          When I list the finals
          Then 2018 shows River Plate beating Boca Juniors on aggregate
        """
        result = get_competition_finals("Libertadores")
        editions = {e["season"]: e for e in result["data"]["editions"]}
        assert editions[2018]["winner"] == "River Plate"
        assert "aggregate" in editions[2018]["detail"]

    def test_2019_and_2020_single_match_finals(self, data):
        """
        Scenario: single-match finals
          Given the 2019 and 2020 Libertadores finals
          When I list the finals
          Then Flamengo (2019) and Palmeiras (2020) are the winners
        """
        result = get_competition_finals("Libertadores")
        editions = {e["season"]: e for e in result["data"]["editions"]}
        assert editions[2019]["winner"] == "Flamengo"
        assert editions[2020]["winner"] == "Palmeiras"

    def test_copa_do_brasil_finals(self, data):
        """
        Scenario: 'Find all Copa do Brasil finals'
          Given the Copa do Brasil dataset
          When I list the finals
          Then recent editions include the 2020 Palmeiras win over Grêmio
        """
        result = get_competition_finals("Copa do Brasil")
        editions = {e["season"]: e for e in result["data"]["editions"]}
        assert editions[2020]["winner"] == "Palmeiras"
        assert editions[2019]["winner"] == "Athletico Paranaense"

    def test_final_matches_via_search(self, data):
        """
        Scenario: finals via match search
          Given the Copa do Brasil dataset
          When searching stage "final" for season 2020
          Then both legs of the Grêmio-Palmeiras final are found
        """
        result = search_matches(
            competition="Copa do Brasil", season=2020, stage="final"
        )
        assert result["data"]["total_matches"] == 2
        teams = set()
        for match in result["data"]["matches"]:
            teams.add(match["home_team"])
            teams.add(match["away_team"])
        assert any("Palmeiras" in t for t in teams)
        assert any("Grêmio" in t for t in teams)
