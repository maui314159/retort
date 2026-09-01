"""Tests asserting that all six CSV files load with the documented shapes."""

from __future__ import annotations

from pathlib import Path

import pytest

from brazilian_soccer_mcp.loaders import (
    DATA_FILES,
    load_all,
    load_br_football_matches,
    load_brasileirao_matches,
    load_copa_do_brasil_matches,
    load_fifa_players,
    load_historical_brasileirao,
    load_libertadores_matches,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "kaggle"


@pytest.fixture(scope="module")
def all_data():
    return load_all(DATA_DIR)


def test_all_data_files_exist():
    for filename in DATA_FILES.values():
        assert (DATA_DIR / filename).exists(), filename


def test_brasileirao_matches_load():
    rows = load_brasileirao_matches(DATA_DIR / DATA_FILES["brasileirao_matches"])
    assert len(rows) == 4180
    sample = rows[0]
    assert sample.competition_key == "brasileirao-serie-a"
    assert sample.home_goals is not None
    assert sample.season is not None
    assert sample.round_label.startswith("Round ")


def test_copa_do_brasil_matches_load():
    rows = load_copa_do_brasil_matches(DATA_DIR / DATA_FILES["copa_do_brasil_matches"])
    assert len(rows) == 1337
    assert all(r.competition_key == "copa-do-brasil" for r in rows)
    assert all(r.round_label.startswith("Round ") for r in rows if r.round_label)


def test_libertadores_matches_load():
    rows = load_libertadores_matches(DATA_DIR / DATA_FILES["libertadores_matches"])
    assert len(rows) == 1255
    stages = {r.stage for r in rows if r.stage}
    assert "final" in stages
    assert "group stage" in stages


def test_br_football_matches_load():
    rows = load_br_football_matches(DATA_DIR / DATA_FILES["br_football_stats"])
    assert len(rows) == 10296
    competition_keys = {r.competition_key for r in rows}
    assert competition_keys == {
        "brasileirao-serie-a", "brasileirao-serie-b", "brasileirao-serie-c",
        "copa-do-brasil",
    }
    with_stats = [r for r in rows if r.stats.get("home_corners") is not None]
    assert with_stats
    assert "halftime_result" in with_stats[0].stats


def test_historical_brasileirao_loads():
    rows = load_historical_brasileirao(DATA_DIR / DATA_FILES["campeonato_2003_2019"])
    assert len(rows) == 6886
    seasons = {r.season for r in rows}
    assert min(seasons) == 2003
    assert max(seasons) == 2019
    assert any(r.venue for r in rows)


def test_fifa_players_load():
    players = load_fifa_players(DATA_DIR / DATA_FILES["fifa_data"])
    assert len(players) == 18207
    neymar = [p for p in players if p.name == "Neymar Jr"]
    assert neymar
    assert neymar[0].overall == 92
    assert neymar[0].nationality == "Brazil"


def test_load_all_combines_every_file(all_data):
    matches, players = all_data
    assert len(matches) == 4180 + 1337 + 1255 + 10296 + 6886
    assert len(players) == 18207


def test_date_formats_are_handled(all_data):
    matches, _ = all_data
    dated = [m for m in matches if m.date is not None]
    assert len(dated) >= len(matches) - 2
    undated = [m for m in matches if m.date is None]
    assert all(m.home_goals is None for m in undated), undated
