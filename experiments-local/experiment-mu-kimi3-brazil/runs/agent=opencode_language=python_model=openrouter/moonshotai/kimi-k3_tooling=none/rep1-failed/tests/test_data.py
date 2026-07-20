"""Unit tests for dataset loading and de-duplication."""

import pandas as pd
import pytest

from brazilian_soccer_mcp.data import (
    BRASILEIRAO_A,
    COPA_DO_BRASIL,
    LIBERTADORES,
    Dataset,
)

ALL_SOURCES = {
    "Brasileirao_Matches.csv",
    "Brazilian_Cup_Matches.csv",
    "Libertadores_Matches.csv",
    "novo_campeonato_brasileiro.csv",
    "BR-Football-Dataset.csv",
}


def test_all_six_csv_files_are_loaded(ds):
    """Every provided CSV contributes rows (success criterion: coverage)."""
    sources = set(ds.matches["source"].unique())
    assert sources == ALL_SOURCES
    assert len(ds.players) > 18_000


def test_unified_match_schema(ds):
    expected = {
        "competition",
        "date",
        "season",
        "round",
        "stage",
        "home_team",
        "away_team",
        "home_canon",
        "away_canon",
        "home_goals",
        "away_goals",
        "source",
    }
    assert set(ds.matches.columns) == expected
    assert pd.api.types.is_datetime64_any_dtype(ds.matches["date"])


def test_no_nulls_in_key_columns(ds):
    key = ["date", "home_canon", "away_canon", "home_goals", "away_goals"]
    assert not ds.matches[key].isna().any().any()


def test_no_self_play_rows(ds):
    assert (ds.matches["home_canon"] != ds.matches["away_canon"]).all()


def test_brasileirao_modern_seasons_have_380_matches(ds):
    """20-team round-robin seasons must not be double-counted."""
    bra = ds.matches[ds.matches["competition"] == BRASILEIRAO_A]
    counts = bra.groupby("season").size()
    for season in range(2006, 2023):
        if season == 2016:
            # One mislabeled row exists in the BR-Football source scrape.
            assert counts[season] in (380, 381)
        else:
            assert counts[season] == 380, f"season {season}: {counts[season]}"


def test_dates_parsed_from_multiple_formats(ds):
    # ISO with time (Brasileirao), DD/MM/YYYY (historical), ISO date (BR).
    hist = ds.matches[ds.matches["source"] == "novo_campeonato_brasileiro.csv"]
    # The historical file is the sole source for 2003-2011; its later
    # seasons mostly de-duplicate against the dedicated Brasileirão file.
    assert hist["date"].min().year == 2003
    assert set(range(2003, 2012)) <= set(hist["season"].unique())
    assert ds.matches["date"].min().year >= 2003
    assert ds.matches["date"].max().year <= 2023


def test_competitions_present(ds):
    comps = set(ds.matches["competition"].unique())
    assert {
        BRASILEIRAO_A,
        "Brasileirão Série B",
        "Brasileirão Série C",
        COPA_DO_BRASIL,
        LIBERTADORES,
    } <= comps


def test_goals_are_integers(ds):
    assert str(ds.matches["home_goals"].dtype) == "Int64"
    assert str(ds.matches["away_goals"].dtype) == "Int64"


def test_player_helper_columns(ds):
    assert "name_norm" in ds.players.columns
    assert "club_canon" in ds.players.columns
    # FIFA club spellings must normalize like match team spellings.
    gremio = ds.players[ds.players["Club"] == "Grêmio"]
    assert len(gremio) > 0
    assert (gremio["club_canon"] == "gremio").all()


def test_dataset_info(ds):
    info = ds.info()
    assert info["total_matches"] == len(ds.matches)
    assert set(info["matches_by_source"]) == ALL_SOURCES
    assert info["total_players"] == len(ds.players)
    assert info["season_range"] == [2003, 2023]


def test_dataset_with_explicit_dir(tmp_path):
    with pytest.raises(FileNotFoundError):
        Dataset(tmp_path / "does-not-exist")
