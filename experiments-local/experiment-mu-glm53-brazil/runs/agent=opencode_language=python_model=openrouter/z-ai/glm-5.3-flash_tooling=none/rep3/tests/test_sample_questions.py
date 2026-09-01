"""Spec success criterion: at least 20 sample questions can be answered.

Each question from TASK.md is routed either through the deterministic
``answer_question`` router or directly to the matching store method; the
assertions check that a meaningful, structured answer comes back.
"""

from __future__ import annotations

import pytest

from brazilian_soccer.store import NotFound, SoccerStore
from brazilian_soccer.tools import answer_question


def _ask(store: SoccerStore, question: str) -> dict:
    return answer_question(store, question)


def test_01_show_all_flamengo_vs_fluminense_matches(store):
    r = _ask(store, "Show me all Flamengo vs Fluminense matches")["result"]
    assert r["total_matches"] > 30
    assert r["matches"]


def test_02_palmeiras_matches_in_2023(store):
    r = store.search_matches(team="Palmeiras", season=2023, limit=50)
    assert r["total"] >= 30
    assert all(m["season"] == 2023 for m in r["matches"])


def test_03_copa_do_brasil_finals(store):
    r = store.search_matches(stage="final", competition="Copa do Brasil",
                             limit=100)
    assert r["total"] >= 20          # ~2 finals per season, 2012-2021
    assert all(m["stage"] == "final" for m in r["matches"])


def test_04_corinthians_home_record_2022(store):
    r = store.team_stats("Corinthians", season=2022,
                         competition="Brasileirão Serie A", venue="home")
    assert r["matches"] == 19        # 38-round season -> 19 home games
    assert r["wins"] + r["draws"] + r["losses"] == 19


def test_05_top_scorer_team_serie_a_2023(store):
    table = store.standings("Brasileirão Serie A", 2023)["table"]
    best = max(table, key=lambda r: r["goals_for"])
    assert best["goals_for"] >= 55   # champions-level scoring


def test_06_compare_palmeiras_santos(store):
    r = store.head_to_head("Palmeiras", "Santos")
    assert r["total_matches"] > 20
    assert r["team_a_wins"] + r["team_b_wins"] + r["draws"] == r["total_matches"]


def test_07_brazilian_players(store):
    r = store.search_players(nationality="brazil", limit=50)
    assert r["total"] > 40
    assert all(p["nationality"] == "Brazil" for p in r["players"])
    overalls = [p["overall"] for p in r["players"]]
    assert overalls == sorted(overalls, reverse=True)


def test_08_top_rated_players_at_cruzeiro(store):
    r = store.players_at_club("Cruzeiro")
    assert r["total_players"] > 10
    assert 60 <= r["average_overall"] <= 85


def test_09_who_won_2019_brasileirao(store):
    r = _ask(store, "Who won the 2019 Brasileirão?")["result"]
    assert r["champion"] == "Flamengo-RJ"


def test_10_2018_libertadores_final(store):
    r = store.search_matches(stage="final", competition="Copa Libertadores",
                             season=2018)
    teams = {m["home"] for m in r["matches"]} | {m["away"] for m in r["matches"]}
    assert {"Boca Juniors", "River Plate"} <= teams


def test_11_relegated_in_2020(store):
    r = store.standings("Brasileirão Serie A", 2020)
    # Botafogo's historically first relegation season.
    assert set(r["relegation_zone"]) == {"Vasco da Gama", "Goiás",
                                         "Coritiba", "Botafogo-RJ"}


def test_12_average_goals_brasileirao(store):
    r = _ask(store, "What's the average goals per match in the Brasileirão?")["result"]
    assert 2.0 <= r["avg_goals_per_match"] <= 3.5


def test_13_best_away_record(store):
    r = _ask(store, "Which team has the best away record?")["result"]
    assert r["best_away_records"][0]["matches"] >= 30


def test_14_biggest_wins(store):
    r = _ask(store, "Show me the biggest wins in the dataset")["result"]
    wins = r["biggest_wins"]
    assert len(wins) == 10
    assert wins[0]["winner"] and wins[0]["score"]


def test_15_when_did_flamengo_last_play_corinthians(store):
    r = _ask(store, "When did Flamengo last play Corinthians?")["result"]
    assert r["total"] >= 40
    # most recent first
    dates = [m["date"] for m in r["matches"]]
    assert dates == sorted(dates, reverse=True)


def test_16_last_clasico_score(store):
    r = store.head_to_head("Flamengo", "Vasco da Gama-RJ", limit=1)
    last = r["matches"][-1]
    assert last["home_goal"] is not None and last["away_goal"] is not None


def test_17_who_is_gabriel_barbosa(store):
    """Spec lookup example - searched by name; this FIFA export does not
    contain him, and the answer is a graceful structured not-found."""
    r = _ask(store, "Who is Gabriel Barbosa?")["result"]
    assert r["found"] is False
    assert "Gabriel Barbosa" in r["message"]


def test_18_who_is_neymar(store):
    r = _ask(store, "Who is Neymar?")["result"]
    assert r["name"] == "Neymar Jr"
    assert r["overall"] == 92


def test_19_players_for_fluminense(store):
    r = store.players_at_club("Fluminense")
    assert r["total_players"] > 0
    assert all(p["club"] for p in r["players"])


def test_20_derbies_in_2023(store):
    r = _ask(store, "Show me all derbies in 2023")["result"]
    names = {d["derby"] for d in r["derbies"]}
    assert {"Fla-Flu", "Grenal", "Dérbi Paulista"} <= names


def test_21_competitions_of_palmeiras(store):
    r = _ask(store, "What competitions has Palmeiras played in?")["result"]
    assert "Brasileirão Serie A" in r["competitions"]
    assert "Copa Libertadores" in r["competitions"]


def test_22_best_home_record(store):
    r = _ask(store, "Which team has the best home record?")["result"]
    best = r["best_home_records"][0]
    assert best["matches"] >= 30 and best["win_rate"] > 50


def test_23_top_brazilian_players(store):
    r = store.search_players(nationality="brazil", min_overall=85, limit=5)
    assert r["players"][0]["name"] == "Neymar Jr"


def test_24_compare_2018_2019_seasons(store):
    r = _ask(store, "Compare the 2018 and 2019 seasons of the Brasileirão")["result"]
    champs = r["champions"]
    assert champs[2018] == "Palmeiras"
    assert champs[2019] == "Flamengo-RJ"


def test_25_unroutable_question_is_reported(store):
    with pytest.raises(NotFound):
        answer_question(store, "What is the meaning of life?")
