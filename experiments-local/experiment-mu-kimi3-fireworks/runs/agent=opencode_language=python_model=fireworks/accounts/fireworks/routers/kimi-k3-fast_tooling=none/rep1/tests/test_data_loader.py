"""Tests for loading and unifying the six CSV datasets."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from brazilian_soccer_mcp.data_loader import (
    BRASILEIRAO_A,
    COPA_DO_BRASIL,
    LIBERTADORES,
    DATA_SUBDIR,
)

DATA_DIR = Path(__file__).resolve().parent.parent / DATA_SUBDIR

# Row counts published in the specification.
RAW_COUNTS = {
    "Brasileirao_Matches.csv": 4180,
    "Brazilian_Cup_Matches.csv": 1337,
    "Libertadores_Matches.csv": 1255,
    "BR-Football-Dataset.csv": 10296,
    "novo_campeonato_brasileiro.csv": 6886,
    "fifa_data.csv": 18207,
}


class TestRawFiles:
    @pytest.mark.parametrize("filename,expected", list(RAW_COUNTS.items()))
    def test_file_row_count(self, filename, expected):
        df = pd.read_csv(DATA_DIR / filename, low_memory=False)
        assert len(df) == expected, f"{filename}: expected {expected} rows, got {len(df)}"

    def test_all_six_files_exist(self):
        for filename in RAW_COUNTS:
            assert (DATA_DIR / filename).exists(), filename


class TestUnifiedMatches:
    def test_schema(self, dataset):
        for col in (
            "date", "home_team", "away_team", "home_key", "away_key",
            "home_goals", "away_goals", "competition", "season", "source",
        ):
            assert col in dataset.matches.columns, col

    def test_all_sources_present(self, dataset):
        sources = set(dataset.matches["source"].unique())
        assert sources == set(RAW_COUNTS) - {"fifa_data.csv"}

    def test_competitions(self, dataset):
        comps = set(dataset.matches["competition"].unique())
        assert {BRASILEIRAO_A, COPA_DO_BRASIL, LIBERTADORES} <= comps

    def test_no_null_scores_or_dates(self, dataset):
        m = dataset.matches
        assert m["home_goals"].notna().all()
        assert m["away_goals"].notna().all()
        assert m["date"].notna().all()

    def test_dedup_no_same_fixture_twice(self, dataset):
        """No pairing (same direction) twice in one competition+season.

        Exception: the histórico file itself lists Botafogo x Flamengo
        twice in 2009 (a source data error), so at most those two rows
        may collide; every other league fixture must be unique.
        """
        m = dataset.matches
        league = m[m["competition"] == BRASILEIRAO_A]
        dup = league[league.duplicated(
            subset=["competition", "season", "home_key", "away_key"], keep=False
        )]
        assert len(dup) <= 2, f"unexpected duplicate fixtures:\n{dup}"
        if len(dup):
            assert set(dup["season"]) == {2009}

    def test_seasons_span_2003_2023(self, dataset):
        seasons = dataset.matches["season"]
        assert int(seasons.min()) == 2003
        assert int(seasons.max()) == 2023

    def test_serie_a_full_seasons_have_380_matches(self, dataset):
        m = dataset.matches
        sa = m[m["competition"] == BRASILEIRAO_A]
        counts = sa.groupby("season").size()
        for year in range(2012, 2023):
            assert counts.loc[year] == 380, f"season {year}: {counts.loc[year]} matches"


class TestPlayers:
    def test_player_count(self, dataset):
        assert len(dataset.players) == 18207

    def test_key_columns(self, dataset):
        for col in ("Name", "Nationality", "Overall", "Club", "Position", "club_key", "position_group"):
            assert col in dataset.players.columns, col

    def test_brazilian_players_present(self, dataset):
        brazil = dataset.players[dataset.players["Nationality"] == "Brazil"]
        assert len(brazil) > 800

    def test_club_keys_normalized(self, dataset):
        p = dataset.players
        gremio = p[p["Club"] == "Grêmio"]
        assert len(gremio) > 0
        assert set(gremio["club_key"]) == {"gremio rs"}


class TestDatasetSummary:
    def test_summary_shape(self, dataset):
        s = dataset.summary()
        assert s["matches"] > 15000
        assert s["players"] == 18207
        assert s["teams"] > 200
        assert 2003 in s["seasons"] and 2023 in s["seasons"]
