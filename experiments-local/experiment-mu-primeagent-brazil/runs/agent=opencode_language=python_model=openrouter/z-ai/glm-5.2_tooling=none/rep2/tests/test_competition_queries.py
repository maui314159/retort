"""BDD tests: competition queries (standings, champion, relegation, cups).

Feature: Competition Queries
  Scenario: Who won the 2019 Brasileirao?
    Given the match data is loaded
    When I request the champion of the 2019 Brasileirao
    Then the champion should be Flamengo with 90 points (28W, 6D, 4L)

  Scenario: Relegation
    Given the match data is loaded
    When I request the relegated teams of the 2019 Brasileirao
    Then I should receive four teams from the bottom of the standings
"""
from __future__ import annotations

from brsl.query_engine import QueryEngine


class TestCompetitionQueries:
    # Scenario: 2019 Brasileirao standings (matches the spec example)
    def test_standings_2019_brasileirao(self, engine: QueryEngine):
        table = engine.standings("brasileirao", 2019)
        rows = table["standings"]
        assert len(rows) == 20
        champion = rows[0]
        assert champion["team"].startswith("Flamengo")
        assert champion["points"] == 90
        assert (champion["wins"], champion["draws"], champion["losses"]) == \
            (28, 6, 4)
        assert champion["champion"] is True
        # standings must be sorted by points descending
        points = [r["points"] for r in rows]
        assert points == sorted(points, reverse=True)

    # Scenario: champion helper
    def test_champion_2019(self, engine: QueryEngine):
        champ = engine.champion("brasileirao", 2019)
        assert champ["champion"].startswith("Flamengo")
        assert champ["points"] == 90
        assert champ["record"] == [28, 6, 4]

    # Scenario: relegated teams
    def test_relegated_2019(self, engine: QueryEngine):
        rel = engine.relegated("brasileirao", 2019, n=4)
        assert len(rel["relegated"]) == 4
        table = engine.standings("brasileirao", 2019)
        bottom = [r["team"] for r in table["standings"][-4:]]
        assert rel["relegated"] == bottom

    # Scenario: standings uses a single clean source (no double counting)
    def test_standings_no_double_count(self, engine: QueryEngine):
        table = engine.standings("brasileirao", 2019)
        # 20 teams * 38 matches = 760 team-match participations
        participations = sum(r["played"] for r in table["standings"])
        assert participations == 760  # 380 matches * 2 sides

    # Scenario: Serie B standings are computable
    def test_serie_b_standings(self, engine: QueryEngine):
        table = engine.standings("Serie B", 2019)
        rows = table["standings"]
        assert len(rows) >= 10
        for r in rows:
            assert r["played"] > 0

    # Scenario: cup bracket returns matches grouped by round/stage
    def test_copa_do_brasil_bracket(self, engine: QueryEngine):
        bracket = engine.cup_bracket("copa do brasil", 2019)
        assert bracket["match_count"] > 0
        assert isinstance(bracket["stages"], dict)
        assert len(bracket["stages"]) > 0

    def test_libertadores_bracket(self, engine: QueryEngine):
        bracket = engine.cup_bracket("libertadores", 2019)
        assert bracket["match_count"] > 0
        assert any(stage for stage in bracket["stages"])
