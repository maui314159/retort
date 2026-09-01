"""GWT tests for competition queries: standings, finals, coverage."""

from __future__ import annotations


class TestStandings:
    def test_given_2019_serie_a_when_standings_computed_then_spec_example_values(self, engine):
        # The specification's example answer: Flamengo 90 pts (28W, 6D, 4L)
        result = engine.standings("Série A", 2019)
        champion = result["champion"]
        assert champion["team"] == "Flamengo (RJ)"
        assert champion["points"] == 90
        assert (champion["wins"], champion["draws"], champion["losses"]) == (28, 6, 4)
        assert result["completeness"] == "complete"
        assert result["matches_counted"] == 380

    def test_given_table_when_computed_then_points_balance(self, engine):
        result = engine.standings("Série A", 2019)
        table = result["table"]
        wins = sum(row["wins"] for row in table)
        draws = sum(row["draws"] for row in table)
        losses = sum(row["losses"] for row in table)
        points = sum(row["points"] for row in table)
        # every win is exactly one loss for the opponent
        assert wins == losses
        # draws are symmetric: two table entries per drawn match
        assert draws % 2 == 0
        # 3 points per decisive match, 1 per drawn match per team
        assert points == 3 * wins + draws
        # double round-robin: matches = wins + draws/2
        assert wins + draws // 2 == result["matches_counted"]

    def test_given_2020_when_standings_computed_then_relegated_are_bottom_four(self, engine):
        result = engine.standings("Série A", 2020)
        relegated = {row["team"] for row in result["relegated"]}
        assert relegated == {"Coritiba (PR)", "Vasco da Gama (RJ)", "Goiás (GO)", "Botafogo (RJ)"}
        table_teams = [row["team"] for row in result["table"]]
        for row in result["relegated"]:
            assert table_teams.index(row["team"]) >= len(table_teams) - 4

    def test_given_historic_seasons_when_standings_computed_then_champions_match_history(self, engine):
        expected_champions = {
            2003: "Cruzeiro (MG)",
            2009: "Flamengo (RJ)",
            2012: "Fluminense (RJ)",
            2014: "Cruzeiro (MG)",
            2016: "Palmeiras (SP)",
            2018: "Palmeiras (SP)",
            2019: "Flamengo (RJ)",
            2020: "Flamengo (RJ)",
            2021: "Atlético Mineiro (MG)",
            2022: "Palmeiras (SP)",
        }
        for season, expected in expected_champions.items():
            result = engine.standings("Série A", season)
            assert result["champion"]["team"] == expected, f"{season}: {result['champion']}"

    def test_given_partial_season_when_standings_computed_then_flagged(self, engine):
        # Série A 2023 exists only in BR-Football with 377 of 380 matches
        result = engine.standings("Série A", 2023)
        assert result["completeness"] == "partial"
        assert "partial" in result["summary"]

    def test_given_serie_b_when_standings_computed_then_two_decade_coverage(self, engine):
        result = engine.standings("Série B", 2023)
        assert result["completeness"] == "complete"
        assert len(result["table"]) == 20

    def test_given_cup_competition_when_standings_requested_then_error(self, engine):
        result = engine.standings("Copa do Brasil", 2019)
        assert "error" in result

    def test_given_unknown_season_when_standings_requested_then_available_seasons_listed(self, engine):
        result = engine.standings("Série A", 1998)
        assert "error" in result
        assert 2003 in result["available_seasons"]


class TestCompetitionFinals:
    def test_given_copa_do_brasil_when_finals_listed_then_two_legged_aggregates(self, engine):
        result = engine.competition_finals("Copa do Brasil")
        years = {final["season"] for final in result["finals"]}
        assert 2012 in years and 2019 in years
        final_2019 = next(f for f in result["finals"] if f["season"] == 2019)
        assert final_2019["winner"] == "Athletico Paranaense (PR)"

    def test_given_libertadores_when_finals_listed_then_all_winners(self, engine):
        result = engine.competition_finals("Libertadores")
        wins = {f["season"]: f["winner"] for f in result["finals"]}
        assert wins[2014] == "San Lorenzo"
        assert wins[2019] == "Flamengo (RJ)"

    def test_given_league_when_finals_requested_then_error(self, engine):
        assert "error" in engine.competition_finals("Série A")


class TestCompetitionInfo:
    def test_given_all_files_when_info_requested_then_full_coverage_listed(self, engine):
        info = engine.competition_info()
        families = set(info["competitions"])
        assert families == {"serie_a", "serie_b", "serie_c", "copa_do_brasil", "libertadores"}
        serie_a = info["competitions"]["serie_a"]
        assert serie_a["seasons"][0] == 2003
        assert serie_a["seasons"][-1] == 2023


class TestTopScoringTeams:
    def test_given_2019_serie_a_when_top_scoring_then_flamengo_leads(self, engine):
        # Flamengo scored 86 goals in the 2019 Brasileirão
        result = engine.top_scoring_teams(competition="Série A", season=2019, limit=5)
        assert result["teams"][0]["team"] == "Flamengo (RJ)"
        assert result["teams"][0]["goals"] == 86
        assert "cannot be derived" in result["summary"]
