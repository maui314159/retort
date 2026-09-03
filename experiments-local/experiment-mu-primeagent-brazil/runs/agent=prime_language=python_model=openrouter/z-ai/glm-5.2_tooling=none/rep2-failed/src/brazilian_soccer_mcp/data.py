"""
Context block
=============
Brazilian Soccer MCP Server - Data Loader
-----------------------------------------
Purpose: Load and normalize all six provided CSV datasets into a single,
queryable in-memory representation.

Datasets (all under data/kaggle/):
  1. Brasileirao_Matches.csv     - Brasileirão Serie A (2012-2022)
  2. Brazilian_Cup_Matches.csv   - Copa do Brasil (2012-2021)
  3. Libertadores_Matches.csv    - Copa Libertadores (2013-2022)
  4. BR-Football-Dataset.csv     - extended match stats (Serie A/B/C + Cup)
  5. novo_campeonato_brasileiro.csv - historical Brasileirão (2003-2019)
  6. fifa_data.csv               - FIFA player database (~18k players)

This module:
  * Reads every CSV with UTF-8 encoding (handling Portuguese accents).
  * Normalizes team names via the normalizer module (canonical keys + display).
  * Normalizes dates across the three different date formats used in the data.
  * Normalizes goals to nullable floats (NaN means "not yet played").
  * Tags every match with a `competition` string.
  * Adds a canonical club key to every FIFA player row for cross-file joins.

It exposes a cached singleton `get_data()` returning a `SoccerData` instance.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

import pandas as pd

from . import normalizer as nz

# Canonical competition names used across the server.
COMP_BRASILEIRAO = "Brasileirão Serie A"
COMP_CUP = "Copa do Brasil"
COMP_LIBERTADORES = "Copa Libertadores"
COMP_HIST = "Brasileirão (2003-2019)"


def _coerce_goal(value) -> Optional[float]:
    """Convert a goal value to a float, returning None for missing/'-' entries."""
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    s = str(value).strip()
    if s == "" or s.lower() in ("nan", "none", "-"):
        return None
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _parse_date(value) -> Optional[pd.Timestamp]:
    """Parse a date/datetime from any of the formats present in the datasets.

    Handles ISO datetime ("2012-05-19 18:30:00"), ISO date ("2023-09-24")
    and Brazilian date ("29/03/2003").
    """
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        return value if not pd.isna(value) else None
    s = str(value).strip()
    if s == "" or s.lower() in ("nan", "none"):
        return None
    # ISO datetime / ISO date first (unambiguous).
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return pd.to_datetime(s, format=fmt)
        except (ValueError, TypeError):
            continue
    # Brazilian day-first date format.
    try:
        return pd.to_datetime(s, dayfirst=True, errors="raise")
    except (ValueError, TypeError):
        return None


def _add_team_columns(df: pd.DataFrame, home_col: str, away_col: str) -> pd.DataFrame:
    """Add canonical key/display columns for home and away teams."""
    df = df.copy()
    df["home_key"] = df[home_col].map(nz.canonical_key)
    df["away_key"] = df[away_col].map(nz.canonical_key)
    df["home_display"] = df[home_col].map(nz.display_name)
    df["away_display"] = df[away_col].map(nz.display_name)
    return df


def _build_frame(df, home_col, away_col, hg_col, ag_col, competition,
                 date_col, season_col, round_col=None, stage_col=None,
                 stadium_col=None, extra_cols=None):
    """Build a normalized match DataFrame from a raw source DataFrame."""
    df = _add_team_columns(df, home_col, away_col)
    out = pd.DataFrame({
        "date": df[date_col].map(_parse_date),
        "season": pd.to_numeric(df[season_col], errors="coerce") if season_col else pd.NA,
        "competition": competition,
        "home_team": df[home_col],
        "away_team": df[away_col],
        "home_display": df["home_display"],
        "away_display": df["away_display"],
        "home_key": df["home_key"],
        "away_key": df["away_key"],
        "home_goal": df[hg_col].map(_coerce_goal),
        "away_goal": df[ag_col].map(_coerce_goal),
        "round": df[round_col] if round_col else pd.NA,
        "stage": df[stage_col] if stage_col else pd.NA,
        "stadium": df[stadium_col] if stadium_col else pd.NA,
    })
    if extra_cols:
        for c in extra_cols:
            if c in df.columns:
                out[c] = df[c].values
    return out


class SoccerData:
    """Holds normalized match and player DataFrames for all datasets."""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.matches: Optional[pd.DataFrame] = None
        self.players: Optional[pd.DataFrame] = None
        self._load()

    # ------------------------------------------------------------------ load
    def _load(self) -> None:
        frames = [
            self._load_brasileirao(),
            self._load_cup(),
            self._load_libertadores(),
            self._load_brf(),
            self._load_historical(),
        ]
        self.matches = pd.concat(frames, ignore_index=True, sort=False)
        self.players = self._load_fifa()

    def _path(self, name: str) -> str:
        return os.path.join(self.data_dir, name)

    def _load_brasileirao(self) -> pd.DataFrame:
        df = pd.read_csv(self._path("Brasileirao_Matches.csv"))
        return _build_frame(df, "home_team", "away_team", "home_goal", "away_goal",
                            COMP_BRASILEIRAO, "datetime", "season", round_col="round")

    def _load_cup(self) -> pd.DataFrame:
        df = pd.read_csv(self._path("Brazilian_Cup_Matches.csv"))
        return _build_frame(df, "home_team", "away_team", "home_goal", "away_goal",
                            COMP_CUP, "datetime", "season", round_col="round")

    def _load_libertadores(self) -> pd.DataFrame:
        df = pd.read_csv(self._path("Libertadores_Matches.csv"))
        return _build_frame(df, "home_team", "away_team", "home_goal", "away_goal",
                            COMP_LIBERTADORES, "datetime", "season", stage_col="stage")

    def _load_brf(self) -> pd.DataFrame:
        df = pd.read_csv(self._path("BR-Football-Dataset.csv"))
        extras = ["home_corner", "away_corner", "home_attack", "away_attack",
                  "home_shots", "away_shots", "ht_result", "at_result",
                  "total_corners"]
        out = _build_frame(df, "home", "away", "home_goal", "away_goal",
                           None, "date", None)
        out["competition"] = df["tournament"].values
        out["season"] = out["date"].dt.year
        for c in extras:
            if c in df.columns:
                out[c] = df[c].values
        return out

    def _load_historical(self) -> pd.DataFrame:
        df = pd.read_csv(self._path("novo_campeonato_brasileiro.csv"))
        return _build_frame(df, "Equipe_mandante", "Equipe_visitante",
                            "Gols_mandante", "Gols_visitante", COMP_HIST,
                            "Data", "Ano", round_col="Rodada", stadium_col="Arena")

    def _load_fifa(self) -> pd.DataFrame:
        df = pd.read_csv(self._path("fifa_data.csv"))
        keep = ["ID", "Name", "Age", "Nationality", "Overall", "Potential",
                "Club", "Position", "Jersey Number", "Height", "Weight",
                "Preferred Foot", "Value", "Wage"]
        cols = [c for c in keep if c in df.columns]
        p = df[cols].copy()
        p["club_key"] = p["Club"].map(nz.canonical_key)
        p["club_display"] = p["Club"].map(nz.display_name)
        for c in ("Overall", "Potential", "Age"):
            p[c] = pd.to_numeric(p[c], errors="coerce")
        return p


@lru_cache(maxsize=4)
def get_data(data_dir: str = None) -> SoccerData:
    """Return a cached SoccerData singleton."""
    if data_dir is None:
        here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        data_dir = os.path.join(here, "data", "kaggle")
    return SoccerData(data_dir)


def reset_cache() -> None:
    """Clear the cached SoccerData singleton (used by tests)."""
    get_data.cache_clear()
