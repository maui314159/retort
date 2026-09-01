"""
Feature: Competition Queries
  As a soccer fan I want standings computed from match results, plus
  champion and relegation outcomes, so questions like "who won the 2019
  Brasileirão?" and "which teams were relegated in 2020?" have answers.
"""

from __future__ import annotations

from brazilian_soccer_mcp.queries import (
    list_competitions,
    list_teams,
    standings,
)


class TestStandings2019:
    """TASK.md example: the 2019 Brasileirão table."""

    def test_champion_is_flamengo_with_90_points(self, ds):
        """
        Scenario: Who won the 2019 Brasileirão?
          Given the match data is loaded
          When I request the Série A 2019 standings
          Then Flamengo is champion with 90 points (28W, 6D, 4L)
        """
        result = standings(ds, "serie_a", 2019)
        assert result["ok"], result
        champion = result["champion"]
        assert champion["team"] == "Flamengo"
        assert champion["points"] == 90
        assert (champion["wins"], champion["draws"], champion["losses"]) == (28, 6, 4)
        assert champion["played"] == 38

    def test_top_three_match_the_spec_example(self, ds):
        """
        Scenario: the podium matches TASK.md's sample answer
          Given the Série A 2019 standings
          Then Santos is 2nd with 74 pts (22W, 8D, 8L)
          And Palmeiras is 3rd with 74 pts (21W, 11D, 6L)
        """
        result = standings(ds, "serie_a", 2019)
        second, third = result["rows"][1], result["rows"][2]
        assert second["team"] == "Santos"
        assert second["points"] == 74 and second["wins"] == 22
        assert third["team"] == "Palmeiras"
        assert third["points"] == 74 and third["draws"] == 11

    def test_table_is_complete_and_consistent(self, ds):
        """
        Scenario: the table is internally consistent
          Given the Série A 2019 standings
          Then 20 teams are ranked over 380 matches
          And each team's played equals wins + draws + losses
          And points equal 3*wins + draws
        """
        result = standings(ds, "serie_a", 2019)
        assert len(result["rows"]) == 20
        assert result["matches_counted"] == 380
        for row in result["rows"]:
            assert row["played"] == row["wins"] + row["draws"] + row["losses"]
            assert row["points"] == 3 * row["wins"] + row["draws"]
            assert row["goal_diff"] == row["goals_for"] - row["goals_against"]
        assert [r["position"] for r in result["rows"]] == list(range(1, 21))


class TestChampionsAndRelegation:
    """TASK.md: "Which teams were relegated in 2020?"."""

    def test_champions_by_season(self, ds):
        """
        Scenario: champions across seasons
          Given the match data is loaded
          Then 2018 was won by Palmeiras (80 pts)
          And 2019 by Flamengo (90 pts)
          And 2020 by Flamengo (71 pts)
          And 2021 by Atlético Mineiro (84 pts)
        """
        expected = {
            2018: ("Palmeiras", 80),
            2019: ("Flamengo", 90),
            2020: ("Flamengo", 71),
            2021: ("Atlético Mineiro", 84),
        }
        for season, (team, points) in expected.items():
            result = standings(ds, "serie_a", season)
            assert result["ok"]
            assert result["champion"]["team"] == team, season
            assert result["champion"]["points"] == points, season

    def test_relegation_2020(self, ds):
        """
        Scenario: Which teams were relegated in 2020?
          Given the match data is loaded
          When I request the 2020 Série A standings
          Then the bottom four are Vasco da Gama, Goiás, Coritiba, Botafogo
        """
        result = standings(ds, "serie_a", 2020)
        assert result["ok"]
        relegated = {row["team"] for row in result["relegated"]}
        assert relegated == {"Vasco da Gama", "Goiás", "Coritiba", "Botafogo"}

    def test_relegation_2019(self, ds):
        """
        Scenario: the 2019 drop zone
          Given the match data is loaded
          Then Cruzeiro, CSA, Chapecoense and Avaí were relegated in 2019
        """
        result = standings(ds, "serie_a", 2019)
        relegated = {row["team"] for row in result["relegated"]}
        assert relegated == {"Cruzeiro", "CSA", "Chapecoense", "Avaí"}

    def test_serie_b_standings(self, ds):
        """
        Scenario: lower divisions compute too
          Given the match data is loaded
          When I request Série B 2019
          Then a full 20-team table is returned
          And Red Bull Bragantino is champion with 75 points
            (BR-Football is the only source for Série B)
        """
        result = standings(ds, "serie_b", 2019)
        assert result["ok"]
        assert len(result["rows"]) == 20
        assert result["champion"]["team"] == "Red Bull Bragantino"
        assert result["champion"]["points"] == 75

    def test_standings_for_2023_note_single_source(self, ds):
        """
        Scenario: 2023 comes only from the BR-Football file
          Given the match data is loaded
          When I request Série A 2023 standings
          Then a 20-row table is computed from the 377 available matches
            (the source file itself is three matches short of a full season)
        """
        result = standings(ds, "serie_a", 2023)
        assert result["ok"]
        assert len(result["rows"]) == 20
        assert result["matches_counted"] == 377

    def test_knockout_competitions_have_no_standings(self, ds):
        """
        Scenario: cups have no league table
          Given the match data is loaded
          When I request Copa do Brasil or Libertadores standings
          Then the answer explains they are knockout competitions
            and points at the stage='final' search instead
        """
        for competition in ("copa_do_brasil", "libertadores"):
            result = standings(ds, competition, 2019)
            assert not result["ok"]
            assert "knockout" in result["error"]

    def test_missing_season_lists_available(self, ds):
        """
        Scenario: a season with no data
          Given the match data is loaded
          When I request Série A 1999
          Then the error lists the seasons actually available
        """
        result = standings(ds, "serie_a", 1999)
        assert not result["ok"]
        assert "2003" in result["error"]


class TestCompetitionDirectory:
    """Scenario: what competitions and seasons does the graph cover?"""

    def test_list_competitions(self, ds):
        """
        Scenario: the competition directory
          Given the match data is loaded
          When I list competitions
          Then all five appear with their season spans and match counts
        """
        result = list_competitions(ds)
        assert result["ok"]
        by_id = {c["id"]: c for c in result["competitions"]}
        assert set(by_id) == {
            "serie_a",
            "serie_b",
            "serie_c",
            "copa_do_brasil",
            "libertadores",
        }
        assert by_id["serie_a"]["first_season"] == 2003
        assert by_id["serie_a"]["last_season"] == 2023
        assert by_id["serie_a"]["matches"] == 8402
        assert by_id["libertadores"]["first_season"] == 2013

    def test_list_teams_for_a_season(self, ds):
        """
        Scenario: participants of one competition season
          Given the match data is loaded
          When I list Série A 2019 teams
          Then exactly the 20 participants are returned
        """
        result = list_teams(ds, competition="serie_a", season=2019)
        assert result["ok"]
        assert result["total"] == 20
        names = {t["name"] for t in result["teams"]}
        assert {"Flamengo", "Palmeiras", "Santos", "Avaí"} <= names

    def test_list_all_teams(self, ds):
        """
        Scenario: the whole club directory
          Given the match data is loaded
          When I list teams without filters
          Then clubs from every competition appear, ordered by matches
        """
        result = list_teams(ds)
        assert result["ok"]
        assert result["total"] > 300
        counts = [t["match_count"] for t in result["teams"]]
        assert counts == sorted(counts, reverse=True)
