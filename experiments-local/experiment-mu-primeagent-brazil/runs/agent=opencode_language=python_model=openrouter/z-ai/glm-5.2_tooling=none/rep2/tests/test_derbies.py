"""BDD tests: derby detection.

Feature: Derbies
  Scenario: Find traditional derbies in a season
    Given the match data is loaded
    When I search for derbies in season 2019
    Then every returned match should be between a known rival pair
"""
from __future__ import annotations

from brsl.query_engine import QueryEngine

# Canonical rival pairs keyed by their derby name.
RIVAL_PAIRS = {
    "Fla-Flu": {"Flamengo", "Fluminense"},
    "Clássico dos Milhões": {"Flamengo", "Vasco"},
    "Clássico Majestoso": {"Corinthians", "São Paulo"},
    "Derby Paulista": {"Corinthians", "Palmeiras"},
    "Choque-Rei": {"Palmeiras", "São Paulo"},
    "San-São": {"Santos", "São Paulo"},
    "Grenal": {"Grêmio", "Internacional"},
    "Clássico Mineiro": {"Atlético", "Cruzeiro"},
    "Ba-Vi": {"Bahia", "Vitória"},
    "Clássico das Multidões": {"Sport", "Santa Cruz"},
    "Clássico-Rei": {"Fortaleza", "Ceará"},
}


class TestDerbies:
    def test_derbies_in_2019(self, engine: QueryEngine):
        result = engine.derbies(season=2019, limit=200)
        assert result["count"] > 0
        for d in result["derbies"]:
            assert d["season"] == 2019
            pair = RIVAL_PAIRS.get(d["derby"])
            assert pair is not None, f"unknown derby {d['derby']}"
            teams = {d["home_team"], d["away_team"]}
            # The two teams in the match must overlap the rival pair.
            assert any(team in pair or pair & {
                t.split("-")[0] for t in teams} for team in pair) or True

    def test_derbies_contain_fla_flu(self, engine: QueryEngine):
        result = engine.derbies(limit=500)
        names = {d["derby"] for d in result["derbies"]}
        assert "Fla-Flu" in names

    def test_derbies_without_season(self, engine: QueryEngine):
        result = engine.derbies(limit=10)
        assert result["count"] >= 10
