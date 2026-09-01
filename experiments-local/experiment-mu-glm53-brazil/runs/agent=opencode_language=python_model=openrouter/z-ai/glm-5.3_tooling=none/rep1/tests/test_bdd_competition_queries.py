"""BDD scenarios: competition queries (spec section 4 - Competition Queries).

Gherkin:

Feature: Competition Queries
  Scenario: Who won the 2019 Brasileirão?
    Given the match data is loaded
    When I request the standings for season 2019
    Then Flamengo should be first with 90 points
"""

from brasil_mcp.store import COPA_DO_BRASIL, LIBERTADORES, SERIE_A


class TestStandings:
    """Scenario: standings by season, calculated from match results."""

    def test_who_won_the_2019_brasileirao(self, ask):
        result = ask("standings", season=2019)
        assert result["champion"]["team"] == "Flamengo"
        assert result["champion"]["points"] == 90
        assert "1. Flamengo - 90 pts (28W, 6D, 4L) - Champion" in result["summary"]

    def test_2019_top_three_matches_history(self, ask):
        result = ask("standings", season=2019)
        top3 = [row["team"] for row in result["table"][:3]]
        assert top3 == ["Flamengo", "Santos", "Palmeiras"]
        assert [row["points"] for row in result["table"][:3]] == [90, 74, 74]

    def test_2020_covid_season_champion(self, ask):
        result = ask("standings", season=2020)
        assert result["champion"]["team"] == "Flamengo"
        assert result["champion"]["points"] == 71

    def test_relegated_teams_2019(self, ask):
        result = ask("standings", season=2019)
        relegated = {row["team"] for row in result["relegated"]}
        assert relegated == {"Cruzeiro", "CSA", "Chapecoense", "Avaí"}

    def test_relegated_teams_2022(self, ask):
        result = ask("standings", season=2022)
        relegated = {row["team"] for row in result["relegated"]}
        assert relegated == {"Ceará", "Atlético-GO", "Avaí", "Juventude"}

    def test_table_internal_consistency(self, ask):
        for season in (2015, 2019, 2021):
            result = ask("standings", season=season)
            assert len(result["table"]) == 20
            for row in result["table"]:
                assert row["points"] == row["wins"] * 3 + row["draws"]
                assert row["matches"] == 38
                assert row["goals_for"] + row["goals_against"] >= row["matches"]

    def test_points_are_monotonically_decreasing(self, ask):
        result = ask("standings", season=2019)
        points = [row["points"] for row in result["table"]]
        assert points == sorted(points, reverse=True)

    def test_historical_seasons_available(self, ask):
        result = ask("standings", season=2003)
        assert result["champion"]["team"] == "Cruzeiro"
        assert result["champion"]["points"] == 100
        assert len(result["table"]) == 24

    def test_serie_b_standings(self, ask):
        result = ask("standings", season=2022, competition="Série B")
        assert result["competition"] == "Brasileirão Série B"
        assert len(result["table"]) == 20
        assert result["champion"]["points"] > 70


class TestLibertadoresBracket:
    """Scenario: Show the 2019 Copa Libertadores bracket."""

    def test_2019_libertadores_stages(self, ask):
        result = ask("standings", season=2019, competition="Libertadores")
        stages = [stage["stage"] for stage in result["stages"]]
        assert stages == [
            "group stage",
            "round of 16",
            "quarterfinals",
            "semifinals",
            "final",
        ]

    def test_2019_libertadores_final(self, ask):
        result = ask("standings", season=2019, competition="Libertadores")
        final = result["stages"][-1]["matches"][0]
        assert final["home_team"] == "Flamengo"
        assert final["away_team"] == "River Plate"
        assert (final["home_goals"], final["away_goals"]) == (2, 1)


class TestCompetitionInfo:
    """Scenario: what competitions and seasons are covered."""

    def test_all_competitions_listed(self, ask):
        result = ask("competition_info")
        names = {row["competition"] for row in result["competitions"]}
        assert names == {SERIE_A, "Brasileirão Série B", "Brasileirão Série C", COPA_DO_BRASIL, LIBERTADORES}

    def test_season_coverage(self, ask):
        result = ask("competition_info")
        rows = {row["competition"]: row for row in result["competitions"]}
        assert rows[SERIE_A]["seasons"] == "2003-2023"
        assert rows[COPA_DO_BRASIL]["matches"] > 1500
        assert rows[LIBERTADORES]["seasons"] == "2013-2022"

    def test_top_scorers_not_available_flagged_by_docs(self, loaded_store):
        """No scorer data exists in the datasets; documented in README."""
        assert not hasattr(loaded_store, "top_scorers"), "datasets contain no scorer info"


class TestCopaDoBrasilSchedule:
    """Scenario: match schedules and results for a cup season."""

    def test_2020_copa_do_brasil_final_round(self, loaded_store, ask):
        """The 2020 final (played in March 2021) must map to season 2020."""
        result = ask("search_matches", competition="Copa do Brasil", season=2020, stage="final", limit=10)
        assert result["total"] == 2
        pairings = {frozenset((m["home_team"], m["away_team"])) for m in result["matches"]}
        assert pairings == {frozenset(("Grêmio", "Palmeiras"))}
        scores = sorted((m["home_goals"], m["away_goals"]) for m in result["matches"])
        assert scores == [(0, 1), (2, 0)]

    def test_finals_query_across_all_seasons(self, ask):
        result = ask("search_matches", competition="Copa do Brasil", stage="final", limit=50)
        assert result["total"] >= 20


class TestAggregatePerformance:
    """Spec: aggregate queries respond in < 5 seconds."""

    def test_standings_under_five_seconds(self, ask):
        import time

        start = time.perf_counter()
        ask("standings", season=2019)
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0, f"standings took {elapsed:.2f}s"
