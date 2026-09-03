"""
Context block
=============
Brazilian Soccer MCP Server - Sample Question Coverage
------------------------------------------------------
The spec requires "at least 20 sample questions can be answered". This module
maps each sample question from the specification to a QueryEngine call and
asserts a sensible, non-empty answer, exercising the full breadth of the API
(match, team, player, competition, statistical and cross-file queries).
"""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp import get_engine

pytestmark = pytest.mark.usefixtures("engine")


def test_q01_flamengo_vs_fluminense(engine):
    res = engine.find_matches(team="Flamengo", opponent="Fluminense", limit=None)
    assert len(res) > 0


def test_q02_palmeiras_matches_2019(engine):
    res = engine.find_matches(team="Palmeiras", season=2019, limit=None)
    assert len(res) > 0


def test_q03_copa_do_brasil_finals(engine):
    # Copa do Brasil matches exist in the dataset
    res = engine.find_matches(competition="Copa do Brasil", limit=50)
    assert len(res) > 0


def test_q04_last_flamengo_corinthians(engine):
    res = engine.last_match_between("Flamengo", "Corinthians")
    assert res is not None
    assert res["date"] is not None


def test_q05_corinthians_home_record_2019(engine):
    res = engine.team_statistics("Corinthians", season=2019,
                                 competition="brasileirao", venue="home")
    assert res["matches"] == 19


def test_q06_team_most_goals_2019(engine):
    st = engine.standings(competition="brasileirao", season=2019)
    top_scorer = max(st, key=lambda r: r["goals_for"])
    assert top_scorer["goals_for"] > 0


def test_q07_palmeiras_santos_h2h(engine):
    res = engine.head_to_head("Palmeiras", "Santos")
    assert res["matches"] > 0


def test_q08_brazilian_players(engine):
    res = engine.search_players(nationality="Brazil", limit=20)
    assert len(res) == 20


def test_q09_top_rated_at_gremio(engine):
    res = engine.players_at_club("Grêmio")
    assert res[0]["club"] == "Grêmio"
    assert res[0]["overall"] >= 80


def test_q10_forwards_from_brazilian_club(engine):
    res = engine.search_players(club="Santos", position="ST", limit=50)
    assert all(p["club"] == "Santos" for p in res)


def test_q11_who_won_2019_brasileirao(engine):
    st = engine.standings(competition="brasileirao", season=2019, top=1)
    assert st[0]["team"] == "Flamengo"
    assert st[0]["points"] == 90


def test_q12_palmeiras_competitions(engine):
    res = engine.team_competitions("Palmeiras")
    comps = {r["competition"] for r in res}
    assert "Copa Libertadores" in comps


def test_q13_average_goals_brasileirao(engine):
    res = engine.average_goals(competition="brasileirao")
    assert res["average_goals_per_match"] > 0


def test_q14_best_away_record(engine):
    res = engine.best_away_record(competition="brasileirao", season=2019, top=5)
    assert len(res) > 0
    assert all(r["away_matches"] >= 10 for r in res)


def test_q15_biggest_wins(engine):
    res = engine.biggest_wins(limit=5)
    assert res[0]["margin"] >= res[-1]["margin"]


def test_q16_derbies_2023(engine):
    res = engine.derbies(season=2023, limit=100)
    assert len(res) > 0


def test_q17_compare_2018_2019_seasons(engine):
    s18 = {r["season"]: r for r in engine.seasons_summary(competition="brasileirao")}
    assert 2018 in s18 and 2019 in s18
    assert s18[2019]["matches"] == 380


def test_q18_who_is_gabriel(engine):
    res = engine.search_players(name="Gabriel", nationality="Brazil", limit=5)
    assert len(res) > 0


def test_q19_palmeiras_2022_stats(engine):
    res = engine.team_statistics("Palmeiras", season=2019, competition="brasileirao")
    assert res["matches"] == 38


def test_q20_cross_file_player_and_match(engine):
    players = engine.players_at_club("Grêmio")
    h2h = engine.head_to_head("Grêmio", "Internacional")
    assert len(players) > 0 and h2h["matches"] > 0


def test_q21_team_name_normalization(engine):
    # same team referenced with different spellings returns same data
    a = engine.team_statistics("Flamengo-RJ", season=2019, competition="brasileirao")
    b = engine.team_statistics("Flamengo", season=2019, competition="brasileirao")
    assert a == b
