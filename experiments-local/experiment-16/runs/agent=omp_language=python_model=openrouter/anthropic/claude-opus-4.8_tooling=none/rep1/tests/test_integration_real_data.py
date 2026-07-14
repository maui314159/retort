"""
================================================================================
Context
--------------------------------------------------------------------------------
Module  : tests.test_integration_real_data
Purpose : Integration checks against the full Kaggle datasets in data/kaggle/.
          These assert known real-world results and the performance budgets from
          the spec, validating dedup, state-aware keys and standings on real
          data. Skipped automatically if the datasets are absent.
================================================================================
"""

from __future__ import annotations

import time

import pytest


def test_all_six_datasets_load(real_graph):
    # Five match files + the player file all contribute.
    sources = {m.source for m in real_graph.matches}
    assert {
        "Brasileirao_Matches.csv",
        "Brazilian_Cup_Matches.csv",
        "Libertadores_Matches.csv",
        "BR-Football-Dataset.csv",
        "novo_campeonato_brasileiro.csv",
    } <= sources
    assert len(real_graph.players) > 10000


def test_2019_brasileirao_champion_is_flamengo(real_graph):
    # Spec's canonical example: Flamengo won 2019 with 90 pts (28W 6D 4L).
    table = real_graph.standings("Brasileirão", 2019)
    assert len(table) == 20
    champ = table[0]
    assert champ.team == "Flamengo"
    assert champ.points == 90
    assert (champ.wins, champ.draws, champ.losses) == (28, 6, 4)
    # 20-team double round-robin => 38 matches each.
    assert champ.matches == 38


def test_dedup_removes_overlapping_sources(real_graph):
    # Each 2019 team plays exactly 38 league matches despite two overlapping
    # source files covering that season.
    table = real_graph.standings("Brasileirão", 2019)
    assert all(r.matches == 38 for r in table)


def test_distinct_atletico_clubs_kept_separate(real_graph):
    mg = real_graph.team_record("Atletico-MG", season=2019)
    pr = real_graph.team_record("Atletico-PR", season=2019)
    assert mg.team != pr.team
    assert mg.matches > 0 and pr.matches > 0


def test_flamengo_fluminense_head_to_head(real_graph):
    h2h = real_graph.head_to_head("Flamengo", "Fluminense")
    assert h2h["total_matches"] > 0
    assert (
        h2h["team_a_wins"] + h2h["team_b_wins"] + h2h["draws"]
        <= h2h["total_matches"]
    )


def test_brazilian_players_search(real_graph):
    players = real_graph.find_players(nationality="Brazil", limit=10)
    assert len(players) == 10
    overalls = [p.overall or 0 for p in players]
    assert overalls == sorted(overalls, reverse=True)


def test_simple_lookup_under_two_seconds(real_graph):
    start = time.perf_counter()
    real_graph.find_matches(team="Flamengo", opponent="Corinthians")
    assert time.perf_counter() - start < 2.0


def test_aggregate_query_under_five_seconds(real_graph):
    start = time.perf_counter()
    real_graph.standings("Brasileirão", 2019)
    real_graph.average_goals("Brasileirão")
    real_graph.best_records(venue="away")
    assert time.perf_counter() - start < 5.0
