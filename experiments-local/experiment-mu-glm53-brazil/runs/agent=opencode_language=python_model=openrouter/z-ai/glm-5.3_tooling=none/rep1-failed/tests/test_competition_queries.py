"""BDD tests for competition queries (spec section: "4. Competition Queries").

Feature: Competition Queries

  Scenario: Standings by season
    Given the match data is loaded
    When I request the 2019 Brasileirão standings
    Then Flamengo should be champion with 90 points (28W, 6D, 4L)
"""

from __future__ import annotations

import pytest

# Champions verifiable in the provided data. 2009 and 2023 are excluded:
# the source files are missing one (2009 Botafogo x Flamengo) and three
# (2023) fixtures respectively, which shifts those tables.
VERIFIED_CHAMPIONS = {
    2003: "Cruzeiro",
    2004: "Santos",
    2005: "Corinthians",
    2006: "São Paulo",
    2007: "São Paulo",
    2008: "São Paulo",
    2010: "Fluminense",
    2011: "Corinthians",
    2012: "Fluminense",
    2013: "Cruzeiro",
    2014: "Cruzeiro",
    2015: "Corinthians",
    2016: "Palmeiras",
    2017: "Corinthians",
    2018: "Palmeiras",
    2019: "Flamengo",
    2020: "Flamengo",
    2021: "Atlético-MG",
    2022: "Palmeiras",
}


class TestStandings:
    """Scenario: Standings by season (calculated from match results)"""

    def test_2019_spec_example(self, svc):
        """The spec's own example: Flamengo 90 pts (28W, 6D, 4L)."""
        result = svc.standings("Brasileirão Série A", 2019)
        assert "2019 Brasileirão Série A" in result
        assert "1. Flamengo - 90 pts (28W, 6D, 4L)" in result
        assert "Champion" in result

    @pytest.mark.parametrize("season", sorted(VERIFIED_CHAMPIONS))
    def test_champions(self, svc, season):
        expected = VERIFIED_CHAMPIONS[season]
        result = svc.standings("brasileirao", season)
        first = next(ln for ln in result.splitlines() if ln.startswith("1. "))
        assert first.startswith(f"1. {expected} - "), (
            f"{season}: expected {expected}, got {first}"
        )

    def test_relegated_teams_2020(self, svc):
        """Spec sample: 'Which teams were relegated in 2020?'"""
        result = svc.standings("Brasileirão Série A", 2020)
        assert "Relegated (bottom 4)" in result
        # Real world 2020 relegated: Coritiba, Botafogo, Vasco, Goiás.
        for club in ("Coritiba", "Botafogo", "Vasco da Gama", "Goiás"):
            assert club in result.split("Relegated (bottom 4): ")[1].split("\n")[0]

    def test_standings_require_season(self, svc):
        result = svc.standings("Brasileirão Série A")
        assert "Please specify a season" in result
        assert "2003" in result and "2023" in result

    def test_standings_knockout_competition(self, svc):
        result = svc.standings("Copa do Brasil", 2019)
        assert "knockout competition" in result

    def test_standings_alias_serie_b(self, svc):
        result = svc.standings("serie b", 2022)
        assert "2022 Brasileirão Série B" in result

    def test_standings_points_math(self, svc):
        result = svc.standings("Brasileirão Série A", 2019)
        # total points in a full 380-match double round robin = 3*380 - draws
        import re

        pts = [int(m) for m in re.findall(r"(\d+) pts", result)]
        assert len(pts) == 20
        assert pts == sorted(pts, reverse=True)

    def test_unknown_competition(self, svc):
        assert "not found" in svc.standings("La Liga", 2019).lower()


class TestFinals:
    """Scenario: Find cup finals"""

    def test_copa_do_brasil_finals(self, svc):
        result = svc.finals(competition="Copa do Brasil")
        assert "2013 Copa do Brasil" in result
        # 2013 final: Flamengo beat Athletico-PR (1-1, 2-0)
        assert "Flamengo 3" in result
        assert "Flamengo wins" in result

    def test_copa_do_brasil_2015_level_aggregate(self, svc):
        """2015 final ended level on aggregate (Palmeiras won on penalties,
        which the dataset does not record)."""
        result = svc.finals(competition="Copa do Brasil", season=2015)
        assert "level" in result

    def test_libertadores_2019_final(self, svc):
        result = svc.finals(competition="Libertadores", season=2019)
        assert "2019-11-23" in result
        assert "Flamengo 2-1 River Plate" in result
        assert "Winner: Flamengo" in result

    def test_libertadores_2022_placeholder(self, svc):
        """The 2022 final (Flamengo x Athletico-PR) is a placeholder row
        without scores - must be reported, not crash."""
        result = svc.finals(competition="Libertadores")
        assert "not computable" in result


class TestListCompetitions:
    def test_lists_all_competitions(self, svc):
        result = svc.list_competitions()
        for comp in (
            "Brasileirão Série A",
            "Série B",
            "Série C",
            "Copa do Brasil",
            "Copa Libertadores",
        ):
            assert comp in result
        assert "18,207 players" in result

    def test_season_coverage(self, svc):
        result = svc.list_competitions()
        assert "2003-2023" in result  # Serie A span
        assert "2013-2022" in result  # Libertadores span
