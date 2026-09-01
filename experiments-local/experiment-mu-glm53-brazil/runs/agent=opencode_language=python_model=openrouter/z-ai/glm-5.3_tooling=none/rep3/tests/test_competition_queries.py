"""
BDD GWT scenarios: competition queries (standings, champions, brackets).

Gherkin counterpart: ``tests/features/competition_queries.feature``.

Covers TASK.md "Required Capabilities" -> "4. Competition Queries":
standings by season calculated from match results, champions, cup finals.
"""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp import service as svc


class TestStandings:
    def test_given_2019_brasileirao_when_computed_then_flamengo_champion_90(self, dataset):
        # Given "Who won the 2019 Brasileirão?"
        # When computing the standings
        table = svc.standings(dataset, "Brasileirão Serie A", 2019)
        # Then Flamengo leads with the 90 points of the famous campaign
        assert table["champion"] == "Flamengo"
        top = table["table"][0]
        assert top["points"] == 90
        assert (top["wins"], top["draws"], top["losses"]) == (28, 6, 4)
        assert top["goals_for"] == 86

    def test_given_2019_brasileirao_when_computed_then_relegation_zone(self, dataset):
        # Given the 2019 bottom four
        table = svc.standings(dataset, "Brasileirão Serie A", 2019)
        # Then the relegated set matches history
        assert set(table["relegated"]) == {"Cruzeiro", "Chapecoense", "CSA", "Avaí"}

    def test_given_tied_points_when_ranked_then_wins_break_tie(self, dataset):
        # Given Santos and Palmeiras both finished 2019 on 74 points
        # When the table is ordered (CBF criteria: points, wins, GD, GF)
        table = svc.standings(dataset, "Brasileirão Serie A", 2019)
        # Then Santos (22 wins) ranks above Palmeiras (21 wins)
        assert table["table"][1]["team"] == "Santos"
        assert table["table"][1]["wins"] == 22
        assert table["table"][2]["team"] == "Palmeiras"
        assert table["table"][2]["wins"] == 21

    def test_given_2020_when_computed_then_relegated_matches_history(self, dataset):
        # Given "Which teams were relegated in 2020?"
        table = svc.standings(dataset, "Brasileirão Serie A", 2020)
        assert set(table["relegated"]) == {"Vasco da Gama", "Goiás", "Coritiba", "Botafogo"}

    def test_given_2021_when_computed_then_atletico_champion(self, dataset):
        # Given the 2021 season
        table = svc.standings(dataset, "Brasileirão Serie A", 2021)
        # Then Atlético Mineiro's title campaign computes correctly
        assert table["champion"] == "Atlético Mineiro"
        assert table["table"][0]["points"] == 84
        assert set(table["relegated"]) == {"Grêmio", "Bahia", "Sport Recife", "Chapecoense"}

    def test_given_incomplete_2023_when_computed_then_caveat_present(self, dataset):
        # Given the 2023 source is missing 3 of 380 matches
        # When computing the standings
        table = svc.standings(dataset, "Brasileirão Serie A", 2023)
        # Then the incompleteness is flagged to the caller
        assert table["scored_matches"] == 377
        assert any("Data incomplete" in n for n in (table["notes"] or []))

    def test_given_2003_when_computed_then_24_team_season(self, dataset):
        # Given the historical 2003 season from the novo dataset
        table = svc.standings(dataset, "Brasileirão Serie A", 2003)
        # Then the 24-team double round-robin is complete
        assert table["team_count"] == 24
        assert table["matches"] == 552

    def test_given_serie_b_when_computed_then_table_returned(self, dataset):
        # Given Serie B exists only in the BR-Football dataset
        # (2022 rows include two one-match bogus teams in the source)
        table = svc.standings(dataset, "Serie B", 2022)
        # Then the table computes: Cruzeiro's real 2022 title campaign
        assert table["team_count"] == 22
        assert table["champion"] == "Cruzeiro"
        assert table["table"][0]["matches"] == 38
        assert table["table"][0]["points"] == 78

    def test_given_home_venue_when_computed_then_home_table(self, dataset):
        # Given "Which team has the best home record?" style questions
        table = svc.standings(dataset, "Brasileirão Serie A", 2019, venue="home")
        # Then every row counts only home matches (19 per team)
        assert all(row["matches"] == 19 for row in table["table"])

    def test_given_away_venue_when_computed_then_away_table(self, dataset):
        # Given "Which team has the best away record?"
        table = svc.standings(dataset, "Brasileirão Serie A", 2019, venue="away")
        assert all(row["matches"] == 19 for row in table["table"])
        assert table["table"][0]["team"] == "Flamengo"  # best away side of 2019

    def test_given_a_cup_when_standings_requested_then_directed_to_bracket(self, dataset):
        # Given cups have no league table
        # When requesting standings for the Copa do Brasil
        # Then the error points at champion()/bracket()
        with pytest.raises(ValueError, match="bracket"):
            svc.standings(dataset, "Copa do Brasil", 2019)

    def test_given_a_missing_season_when_computed_then_error(self, dataset):
        with pytest.raises(ValueError, match="No matches found"):
            svc.standings(dataset, "Brasileirão Serie A", 1998)


class TestChampions:
    def test_given_league_season_when_champion_requested_then_table_leader(self, dataset):
        assert svc.champion(dataset, "Brasileirão Serie A", 2019)["champion"] == "Flamengo"
        assert svc.champion(dataset, "Brasileirão", 2021)["champion"] == "Atlético Mineiro"

    def test_given_libertadores_2019_when_champion_requested_then_flamengo(self, dataset):
        # Given the 2019 single-match final
        champ = svc.champion(dataset, "Libertadores", 2019)
        # Then Flamengo (2-1 over River Plate) is the winner
        assert champ["champion"] == "Flamengo"
        assert len(champ["final_matches"]) == 1

    def test_given_libertadores_2018_when_champion_requested_then_river_plate(self, dataset):
        # Given the 2018 two-legged Superclásico final
        champ = svc.champion(dataset, "Copa Libertadores", 2018)
        # Then River Plate wins on aggregate (2-2, 3-1)
        assert champ["champion"] == "River Plate"
        assert champ["aggregate"] == {"River Plate": 5, "Boca Juniors": 3}

    def test_given_libertadores_2013_when_aggregate_tied_then_penalties_note(self, dataset):
        # Given the 2013 final ended 2-2 on aggregate
        champ = svc.champion(dataset, "Copa Libertadores", 2013)
        # Then the winner is honestly reported as penalty-decided
        assert champ["champion"] is None
        assert "penalties" in champ["note"]

    def test_given_copa_do_brasil_2019_when_champion_requested_then_athletico(self, dataset):
        # Given the 2019 two-legged cup final
        champ = svc.champion(dataset, "Copa do Brasil", 2019)
        # Then Athletico Paranaense wins on aggregate 3-1
        assert champ["champion"] == "Athletico Paranaense"
        assert champ["aggregate"] == {"Athletico Paranaense": 3, "Internacional": 1}

    def test_given_incomplete_cup_season_when_champion_requested_then_none(self, dataset):
        # Given the 2021 cup data cuts off before the final
        champ = svc.champion(dataset, "Copa do Brasil", 2021)
        # Then no champion is claimed
        assert champ["champion"] is None
        assert champ["note"]


class TestBrackets:
    def test_given_libertadores_2018_when_bracket_requested_then_knockout_rounds(self, dataset):
        # Given "Show the 2018 Copa Libertadores bracket"
        # When requesting the bracket
        bracket = svc.bracket(dataset, "Copa Libertadores", 2018)
        # Then knockout rounds are listed final-first
        assert [r["round"] for r in bracket["rounds"]] == [
            "Final",
            "Semifinals",
            "Quarterfinals",
            "Round Of 16",
        ]
        assert [len(r["matches"]) for r in bracket["rounds"]] == [2, 4, 8, 16]
        assert bracket["group_stage_matches"] == 96

    def test_given_copa_do_brasil_2019_when_bracket_requested_then_final_labeled(self, dataset):
        # Given the 2019 cup
        bracket = svc.bracket(dataset, "Copa do Brasil", 2019)
        # Then the top round is the two-legged final
        assert bracket["rounds"][0]["round"] == "Final"
        assert len(bracket["rounds"][0]["matches"]) == 2

    def test_given_a_league_when_bracket_requested_then_error(self, dataset):
        with pytest.raises(ValueError, match="league"):
            svc.bracket(dataset, "Brasileirão Serie A", 2019)


class TestCompetitionInfo:
    def test_given_no_argument_when_info_requested_then_all_competitions(self, dataset):
        # Given the whole dataset
        info = svc.competition_info(dataset)
        # Then all five competitions are described
        assert set(info["competitions"]) == {
            "Brasileirão Serie A",
            "Brasileirão Serie B",
            "Brasileirão Serie C",
            "Copa do Brasil",
            "Copa Libertadores",
        }

    def test_given_serie_a_when_info_requested_then_season_timeline(self, dataset):
        # Given the Brasileirão
        info = svc.competition_info(dataset, "Brasileirão Serie A")
        # Then seasons span 2003-2023 with a champion per season
        seasons = [s["season"] for s in info["competitions"]["Brasileirão Serie A"]["seasons"]]
        assert seasons[0] == 2003
        assert seasons[-1] == 2023
        by_year = {s["season"]: s for s in info["competitions"]["Brasileirão Serie A"]["seasons"]}
        assert by_year[2019]["champion"] == "Flamengo"
        assert by_year[2019]["matches"] == 380

    def test_given_libertadores_when_info_requested_then_champions_or_notes(self, dataset):
        info = svc.competition_info(dataset, "libertadores")
        seasons = {s["season"]: s for s in info["competitions"]["Copa Libertadores"]["seasons"]}
        assert seasons[2019]["champion"] == "Flamengo"
        assert seasons[2013]["champion"] is None  # penalties-decided
