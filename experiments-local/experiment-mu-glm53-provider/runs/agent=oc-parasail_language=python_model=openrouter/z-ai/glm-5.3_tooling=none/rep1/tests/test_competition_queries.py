"""Feature: Competition Queries
  Scenario: Standings calculated from match results
    Given the match data is loaded
    When I request the standings for the 2019 Brasileirão
    Then Flamengo should be champion with 90 points
    And the table should show wins, draws, losses and goals
  (plus season coverage, relegation and partial-data flags)
"""

import pytest

from brazilian_soccer import queries
from brazilian_soccer.queries import QueryError


class TestStandings:
    def test_2019_brasileirao_standings(self, repo):
        # Given the match data is loaded
        # When I request the standings for the 2019 Brasileirão
        table = queries.standings(repo, competition="Brasileirão Serie A", season=2019)
        # Then the table is complete and correct
        assert table["matches_counted"] == 380
        assert table["teams"] == 20
        assert table["data_complete"] is True
        champion = table["table"][0]
        assert champion["team"] == "Flamengo"
        assert champion["status"] == "champion"
        assert champion["points"] == 90
        assert champion["wins"] == 28
        assert champion["draws"] == 6
        assert champion["losses"] == 4

    def test_relegation_zone_2019(self, repo):
        # Given the 2019 Brasileirão
        table = queries.standings(repo, competition="serie a", season=2019)
        # When the bottom of the table is inspected
        relegated = set(table["relegated"])
        # Then the four relegated clubs include Cruzeiro and CSA
        assert len(relegated) == 4
        assert {"Cruzeiro", "CSA"} <= relegated
        statuses = [row["status"] for row in table["table"][-4:]]
        assert statuses == ["relegated"] * 4

    @pytest.mark.parametrize(
        "season, expected_champion",
        [
            (2003, "Cruzeiro"),
            (2012, "Fluminense"),
            (2015, "Corinthians"),
            (2018, "Palmeiras"),
            (2021, "Atlético-MG"),
            (2022, "Palmeiras"),
        ],
    )
    def test_known_champions_across_eras(self, repo, season, expected_champion):
        # Given historical Brasileirão seasons from three different source files
        # When the standings are calculated from match results
        table = queries.standings(repo, competition="Brasileirão Serie A", season=season)
        # Then the real-world champion emerges for every complete season
        assert table["champion"] == expected_champion

    def test_table_rows_are_consistent(self, repo):
        # Given the 2018 Brasileirão
        table = queries.standings(repo, competition="serie a", season=2018)
        # When the table is inspected
        # Then every row is internally consistent and sorted by points
        points = [row["points"] for row in table["table"]]
        assert points == sorted(points, reverse=True)
        for row in table["table"]:
            assert row["wins"] + row["draws"] + row["losses"] == row["matches"]
            assert row["points"] == 3 * row["wins"] + row["draws"]
            assert row["goal_diff"] == row["goals_for"] - row["goals_against"]
        total_matches = sum(row["matches"] for row in table["table"]) / 2
        assert total_matches == table["matches_counted"]

    def test_partial_season_is_flagged(self, repo):
        # Given the 2022 season, whose source file stops before the final rounds
        table = queries.standings(repo, competition="serie a", season=2022)
        # When the standings are calculated
        # Then incompleteness is reported rather than hidden
        assert table["matches_counted"] == 299
        assert table["data_complete"] is False
        assert "Partial data" in table["note"]

    def test_series_b_standings(self, repo):
        # Given the 2023 Serie B from the statistics file
        table = queries.standings(repo, competition="serie b", season=2023)
        # When calculated from match results
        # Then a full season table emerges with the real champion on top
        assert table["matches_counted"] == 380
        assert table["champion"] == "Vitória"
        assert table["source"] == "BR-Football-Dataset.csv"

    def test_unknown_season_lists_alternatives(self, repo):
        # Given a season with no data
        # When standings are requested
        # Then the error lists what is available
        with pytest.raises(QueryError, match="Available"):
            queries.standings(repo, competition="libertadores", season=2012)


class TestCompetitionInfo:
    def test_list_all_competitions(self, repo):
        # Given the loaded repository
        info = queries.competition_info(repo)
        # When competitions are listed
        # Then all five competitions appear with season coverage
        names = {entry["competition"] for entry in info["competitions"]}
        assert names == {
            "Brasileirão Serie A",
            "Brasileirão Serie B",
            "Brasileirão Serie C",
            "Copa do Brasil",
            "Copa Libertadores",
        }

    def test_competition_season_coverage(self, repo):
        # Given a specific competition
        info = queries.competition_info(repo, competition="libertadores")
        # When inspected
        # Then its seasons and match counts are reported
        seasons = sorted(info["seasons"], key=int)
        assert seasons[0] == "2013"
        assert seasons[-1] == "2022"
        assert info["total_matches"] == 1253

    def test_competition_aliases_accepted(self, repo):
        for alias in ["Brasileirão Serie A", "brasileirao", "serie a", "campeonato brasileiro"]:
            info = queries.competition_info(repo, competition=alias)
            assert info["competition"] == "Brasileirão Serie A"

    def test_unknown_competition_raises(self, repo):
        with pytest.raises(QueryError, match="Unknown competition"):
            queries.competition_info(repo, competition="La Liga")
