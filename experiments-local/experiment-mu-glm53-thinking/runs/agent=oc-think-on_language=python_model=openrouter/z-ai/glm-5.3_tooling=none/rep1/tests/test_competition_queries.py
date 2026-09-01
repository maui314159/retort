"""Feature: Competition Queries

BDD scenarios for the TASK.md examples:
- "Who won the 2019 Brasileirão?"
- "Which teams were relegated in 2020?"
- "Find all Copa do Brasil finals"
- Standings calculated from match results.
"""

from __future__ import annotations

import pytest

from brazilian_soccer import queries as q
from brazilian_soccer.normalize import TeamResolutionError


class TestStandings:
    """Feature: Competition Queries - Scenario: standings by season."""

    def test_2019_brasileirao_champion(self, soccer):
        """Scenario: 'Who won the 2019 Brasileirão?'"""
        # Given the match data is loaded
        # When I request the 2019 Série A standings
        result = q.standings(soccer, "Brasileirão Série A", 2019)
        # Then Flamengo is champion with the historical 90 points
        assert result["champion"] == "Flamengo"
        top = result["table"][0]
        assert top["points"] == 90
        assert (top["wins"], top["draws"], top["losses"]) == (28, 6, 4)
        assert (top["goals_for"], top["goals_against"]) == (86, 37)
        assert top["position"] == 1
        assert result.get("data_note") is None  # complete season

    def test_2019_table_is_a_complete_round_robin(self, soccer):
        # Given the 2019 Série A
        # When the table is calculated
        result = q.standings(soccer, "Série A", 2019)
        # Then 20 teams each played 38 matches and points are consistent
        assert len(result["table"]) == 20
        assert all(row["matches"] == 38 for row in result["table"])
        for row in result["table"]:
            assert row["matches"] == row["wins"] + row["draws"] + row["losses"]
            assert row["points"] == 3 * row["wins"] + row["draws"]
            assert row["goal_diff"] == row["goals_for"] - row["goals_against"]
        positions = [row["position"] for row in result["table"]]
        assert positions == list(range(1, 21))

    def test_2019_relegation_zone(self, soccer):
        # Given the 2019 Série A table
        # When the bottom four are read
        result = q.standings(soccer, "Série A", 2019)
        # Then the historically relegated clubs are flagged
        assert set(result["relegated_bottom_4"]) == {
            "Cruzeiro", "Chapecoense", "CSA", "Avaí",
        }

    def test_2020_relegated_teams(self, soccer):
        """Scenario: 'Which teams were relegated in 2020?'"""
        # Given the 2020 Série A
        # When I request the relegation zone
        result = q.relegated_teams(soccer, "Série A", 2020)
        # Then Vasco, Goiás, Coritiba and Botafogo went down
        assert set(result["relegated"]) == {
            "Vasco da Gama", "Goiás", "Coritiba", "Botafogo",
        }
        assert result["relegated"] == [row["team"] for row in result["bottom_rows"]]

    def test_2023_incomplete_season_is_flagged(self, soccer):
        # Given the 2023 Série A data is missing fixtures
        # When the standings are calculated
        result = q.standings(soccer, "Série A", 2023)
        # Then the table is still produced but the gap is disclosed
        assert len(result["table"]) == 20
        assert "incomplete" in result["data_note"]

    def test_standings_for_a_knockout_cup_are_rejected(self, soccer):
        # Given the Copa do Brasil is a knockout competition
        # When I request standings
        # Then a helpful error points to find_finals
        with pytest.raises(TeamResolutionError, match="knockout"):
            q.standings(soccer, "Copa do Brasil", 2019)

    def test_standings_for_an_unknown_season_are_rejected(self, soccer):
        with pytest.raises(TeamResolutionError, match="No .* matches found"):
            q.standings(soccer, "Série A", 1998)


class TestFindFinals:
    """Feature: Competition Queries - Scenario: 'Find all Copa do Brasil finals'."""

    def test_libertadores_2018_final(self, soccer):
        # Given the Libertadores match data is loaded
        # When I ask for the 2018 finals
        result = q.find_finals(soccer, "Libertadores", 2018)
        # Then the two-legged Boca Juniors x River Plate final is returned
        entry = result["finals"][0]
        assert entry["season"] == 2018
        pairings = [{m["home"], m["away"]} for m in entry["matches"]]
        assert pairings == [{"Boca Juniors", "River Plate"}, {"River Plate", "Boca Juniors"}]
        assert entry["winner_on_aggregate"] == "River Plate"

    def test_all_libertadores_finals(self, soccer):
        # Given the Libertadores data is loaded
        # When I ask for every final
        result = q.find_finals(soccer, "Copa Libertadores")
        # Then finals from 2013 onward are listed with winners where recorded
        seasons = [f["season"] for f in result["finals"]]
        assert 2018 in seasons and 2019 in seasons
        winners = {f["season"]: f["winner_on_aggregate"] for f in result["finals"]}
        assert winners[2019] == "Flamengo"
        assert winners[2020] == "Palmeiras"
        assert None in seasons  # the 2022 final row has no recorded season/score

    def test_copa_do_brasil_finals(self, soccer):
        # Given the Copa do Brasil data is loaded
        # When I ask for the 2020 finals
        result = q.find_finals(soccer, "Copa do Brasil", 2020)
        # Then the two-legged final is returned and Palmeiras won on aggregate
        entry = result["finals"][0]
        assert entry["season"] == 2020
        assert entry["winner_on_aggregate"] == "Palmeiras"
        assert len(entry["matches"]) == 2

    def test_copa_do_brasil_final_list(self, soccer):
        # Given the Copa do Brasil data covers 2012-2021
        # When I ask for all finals
        result = q.find_finals(soccer, "Copa do Brasil")
        # Then every season appears, with honest notes where needed
        by_season = {f["season"]: f for f in result["finals"]}
        assert by_season[2012]["winner_on_aggregate"] == "Palmeiras"
        assert by_season[2020]["winner_on_aggregate"] == "Palmeiras"
        # 2015 and 2017 ended level on recorded goals (penalty shootouts)
        assert by_season[2015]["winner_on_aggregate"] is None
        assert "tie" in by_season[2015]["note"]
        # 2021 data ends before the final
        assert by_season[2021]["matches"] == []
        assert "not in the dataset" in by_season[2021]["note"]

    def test_league_finals_note(self, soccer):
        # Given the Brasileirão is a league
        # When I ask for its finals
        result = q.find_finals(soccer, "Série A", 2019)
        # Then the response points to the standings instead
        assert result["finals"] == []
        assert "standings" in result["note"]


class TestCompetitionsOverview:
    """Feature: Competition Queries - data coverage."""

    def test_all_competitions_are_listed(self, soccer):
        # Given the datasets are loaded
        # When I list competitions
        result = q.competitions_overview(soccer)
        # Then all five competitions appear with seasons and totals
        names = {c["competition"] for c in result["competitions"]}
        assert names == {
            "Brasileirão Série A",
            "Brasileirão Série B",
            "Brasileirão Série C",
            "Copa do Brasil",
            "Copa Libertadores",
        }
        totals = {c["competition"]: c["total_matches"] for c in result["competitions"]}
        assert totals["Brasileirão Série A"] == 8403
        assert totals["Copa Libertadores"] == 1255
        assert result["players"] == 18207

    def test_season_coverage_per_competition(self, soccer):
        # Given the competitions overview
        # When I inspect the Brasileirão Série A seasons
        result = q.competitions_overview(soccer)
        serie_a = next(
            c for c in result["competitions"] if c["competition"] == "Brasileirão Série A"
        )
        seasons = [s["season"] for s in serie_a["seasons"]]
        # Then the historical files provide 2003 through 2023 with no duplicates
        assert seasons == list(range(2003, 2024))
        assert sum(s["matches"] for s in serie_a["seasons"]) == serie_a["total_matches"]
