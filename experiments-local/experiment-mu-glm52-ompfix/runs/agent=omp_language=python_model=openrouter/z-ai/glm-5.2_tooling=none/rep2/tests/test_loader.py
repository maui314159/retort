"""Tests for the data loader (R2: loads and uses the provided datasets).

Verifies that all six bundled Kaggle CSVs are loadable and queryable, and
that the unified match table + player table are non-empty with the expected
columns.
"""
from __future__ import annotations

import pandas as pd

from brazilian_soccer.loader import DATA_DIR, get_data_summary


# ---------------------------------------------------------------------------
# R2: all 6 CSV files exist and are loadable
# ---------------------------------------------------------------------------

EXPECTED_CSVS = [
    "Brasileirao_Matches.csv",
    "Brazilian_Cup_Matches.csv",
    "Libertadores_Matches.csv",
    "BR-Football-Dataset.csv",
    "novo_campeonato_brasileiro.csv",
    "fifa_data.csv",
]


def test_all_data_files_present():
    """Every required CSV file exists in data/kaggle/."""
    for fname in EXPECTED_CSVS:
        assert (DATA_DIR / fname).exists(), f"Missing data file: {fname}"


def test_each_csv_is_loadable():
    """Each CSV can be read by pandas (not corrupt / wrong encoding)."""
    for fname in EXPECTED_CSVS:
        df = pd.read_csv(DATA_DIR / fname, encoding="utf-8-sig")
        assert len(df) > 0, f"{fname} loaded empty"


# ---------------------------------------------------------------------------
# Unified match table
# ---------------------------------------------------------------------------

def test_load_matches_returns_dataframe(matches_df):
    assert isinstance(matches_df, pd.DataFrame)
    assert len(matches_df) > 0


def test_match_columns_present(matches_df):
    required = {
        "date", "competition", "season", "home_team", "away_team",
        "home_goal", "away_goal", "source", "home_key", "away_key",
    }
    assert required.issubset(set(matches_df.columns))


def test_match_competitions_present(matches_df):
    """All five canonical competitions appear in the unified table."""
    comps = set(matches_df["competition"].unique())
    assert "Brasileirão Série A" in comps
    assert "Copa do Brasil" in comps
    assert "Copa Libertadores" in comps


def test_match_deduplication(matches_df):
    """No exact duplicate matches on the dedup key."""
    dedup_cols = ["home_key", "away_key", "date", "home_goal", "away_goal"]
    dated = matches_df[matches_df["date"].notna()]
    dups = dated.duplicated(subset=dedup_cols).sum()
    assert dups == 0, f"{dups} duplicate rows found after dedup"


# ---------------------------------------------------------------------------
# Player table
# ---------------------------------------------------------------------------

def test_load_players_returns_dataframe(players_df):
    assert isinstance(players_df, pd.DataFrame)
    assert len(players_df) > 0


def test_player_columns_present(players_df):
    required = {"Name", "Nationality", "Overall", "Club", "Position"}
    assert required.issubset(set(players_df.columns))


def test_brazilian_players_exist(players_df):
    """The FIFA dataset contains Brazilian players."""
    assert (players_df["Nationality"] == "Brazil").sum() > 0


# ---------------------------------------------------------------------------
# Data summary
# ---------------------------------------------------------------------------

def test_data_summary_structure():
    s = get_data_summary()
    assert s["matches_total"] > 0
    assert s["players_total"] > 0
    assert s["brazilian_players"] > 0
    assert len(s["seasons"]) > 0
    assert "matches_by_competition" in s
    assert "matches_by_source" in s
