"""BDD scenarios for competition queries (standings, relegation, seasons)."""

import soccer.queries as q


class TestStandings:
    def test_2019_brasileirao_champion(self, data):
        """Scenario: who won the 2019 Brasileirão?"""
        table = q.standings(data, 2019)
        rows = table["standings"]
        assert rows[0]["team"] == "Flamengo"
        assert rows[0]["champion"] is True
        assert rows[0]["points"] >= 90
        # points = 3*wins + draws
        for row in rows:
            assert row["points"] == 3 * row["wins"] + row["draws"]
            assert row["matches"] == row["wins"] + row["draws"] + row["losses"]

    def test_standings_are_sorted_by_points(self, data):
        rows = q.standings(data, 2018)["standings"]
        pts = [r["points"] for r in rows]
        assert pts == sorted(pts, reverse=True)

    def test_2018_libertadores_present(self, data):
        """Palmeiras won the 2018 Copa Libertadores - data should cover it."""
        r = q.find_matches(data, competition="Libertadores", season=2018)
        assert r["total"] > 20


class TestRelegated:
    def test_relegation_zone_2020(self, data):
        """Scenario: which teams were relegated in 2020?"""
        r = q.relegated(data, 2020)
        relegated = {row["team"] for row in r["relegated"]}
        assert "Coritiba" in relegated
        assert len(relegated) == 4


class TestCompetitionSeasons:
    def test_seasons_covered(self, data):
        s = q.competition_seasons(data, "Brasileirão")
        assert 2012 in s["seasons"]
        assert s["seasons"] == sorted(s["seasons"])

    def test_historical_data_extends_back_to_2003(self, data):
        s = q.competition_seasons(data, "Brasileirão")
        assert s["seasons"][0] <= 2003
