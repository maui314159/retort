"""
Context block
=============
Module: brazilian_soccer.data_loader
Purpose: Load, clean and normalize the six supplied Kaggle CSV datasets that
         back the Brazilian Soccer MCP server, and expose a single cached
         ``DataStore`` object used by every query function.

Datasets loaded (all from ``data/kaggle/``):
  1. Brasileirao_Matches.csv        - Serie A matches 2012-2022
  2. Brazilian_Cup_Matches.csv      - Copa do Brasil matches 2012-2021
  3. Libertadores_Matches.csv      - Copa Libertadores matches 2013-2022
  4. BR-Football-Dataset.csv       - extended match statistics (4 tournaments)
  5. novo_campeonato_brasileiro.csv- historical Serie A 2003-2019
  6. fifa_data.csv                 - FIFA player database (~18k players)

Normalization performed:
  * Team names: strip trailing state/country suffixes (``-SP``, `` - RJ``),
    drop parentheticals (``(URU)``, ``(antigo ...)``), fold accents and case
    into a stable ``*_norm`` key used for matching across files.
  * Dates: parse ISO datetimes, ``DD/MM/YYYY`` Brazilian dates, and the
    separate date/time columns of the extended dataset into a single
    ``pd.Timestamp`` column (NaT when missing).
  * Goals: coerced to numeric; non-numeric sentinels (``-``) become NaN and
    are excluded from aggregates but still listed as match rows.
  * Competitions: every match row is tagged with a canonical competition name
    (``Brasileirao`` / ``Copa do Brasil`` / ``Libertadores`` / ``Serie B`` /
    ``Serie C``) so competition filters span all files.

The module intentionally has *no* MCP dependency so it can be unit-tested in
isolation and reused by ``brazilian_soccer.queries`` and ``server.py``.
"""

from __future__ import annotations

import os
import re
import unicodedata
from functools import lru_cache
from typing import Optional

import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Resolve the data directory relative to this file so the package works no
# matter where it is imported from.
_DEFAULT_DATA_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir, "data", "kaggle")
)

# Canonical competition names used throughout the query layer.
COMP_BRASILEIRAO = "Brasileirao"
COMP_COPA_DO_BRASIL = "Copa do Brasil"
COMP_LIBERTADORES = "Libertadores"
COMP_SERIE_B = "Serie B"
COMP_SERIE_C = "Serie C"

# Map the many user-facing competition aliases to the canonical names so the
# competition filter is tolerant of accents / English names / Serie A wording.
COMPETITION_ALIASES: dict[str, str] = {
    "brasileirao": COMP_BRASILEIRAO,
    "brasileirão": COMP_BRASILEIRAO,
    "serie a": COMP_BRASILEIRAO,
    "série a": COMP_BRASILEIRAO,
    "campeonato brasileiro": COMP_BRASILEIRAO,
    "campeonato brasileiro serie a": COMP_BRASILEIRAO,
    "copa do brasil": COMP_COPA_DO_BRASIL,
    "copa do brazil": COMP_COPA_DO_BRASIL,
    "brazilian cup": COMP_COPA_DO_BRASIL,
    "cup": COMP_COPA_DO_BRASIL,
    "libertadores": COMP_LIBERTADORES,
    "copa libertadores": COMP_LIBERTADORES,
    "libertadores da america": COMP_LIBERTADORES,
    "serie b": COMP_SERIE_B,
    "série b": COMP_SERIE_B,
    "serie c": COMP_SERIE_C,
    "série c": COMP_SERIE_C,
}


# ---------------------------------------------------------------------------
# Team-name normalization
# ---------------------------------------------------------------------------

# Trailing state/country code, e.g. "-SP", " - RJ", "-EQU" (2-3 letters).
_SUFFIX_RE = re.compile(r"\s*-\s*[A-Za-z]{2,3}\s*$")
# Parenthetical fragments, e.g. "(URU)", "(antigo Esporte Clube Barreira)".
_PAREN_RE = re.compile(r"\s*\([^)]*\)\s*")


def normalize_team(name: object) -> str:
    """Return a stable, accent/case/suffix-insensitive key for a team name.

    Examples
    --------
normalize_team("Palmeiras-SP")
    'palmeiras'
normalize_team("Boavista Sport Club (antigo ...) - RJ")
    'boavista sport club'
normalize_team("São Paulo")
    'sao paulo'
normalize_team(None)
    ''
    """
    if not isinstance(name, str):
        return ""
    s = name.strip()
    s = _PAREN_RE.sub(" ", s)
    s = _SUFFIX_RE.sub("", s)
    # Fold accents to ASCII (NFKD split + drop combining marks).
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s).strip().lower()


def canonical_competition(value: object) -> str:
    """Map a raw/user-facing competition string to a canonical name."""
    if not isinstance(value, str):
        return ""
    key = normalize_team(value)  # accent/case-insensitive
    if key in COMPETITION_ALIASES:
        return COMPETITION_ALIASES[key]
    # also accept already-canonical names directly
    canon = {normalize_team(v): v for v in COMPETITION_ALIASES.values()}
    return canon.get(key, value.strip())


# ---------------------------------------------------------------------------
# Column helpers
# ---------------------------------------------------------------------------

def _to_int_goals(series: pd.Series) -> pd.Series:
    """Coerce a goal column to nullable Int64, turning sentinels into NaN."""
    return pd.to_numeric(series, errors="coerce").astype("Int64")


def _to_int_season(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype("Int64")


# ---------------------------------------------------------------------------
# Per-file loaders -> normalized DataFrame fragments
# ---------------------------------------------------------------------------

def _load_brasileirao(data_dir: str) -> pd.DataFrame:
    df = pd.read_csv(os.path.join(data_dir, "Brasileirao_Matches.csv"))
    out = pd.DataFrame({
        "source": "Brasileirao_Matches.csv",
        "competition": COMP_BRASILEIRAO,
        "competition_raw": COMP_BRASILEIRAO,
        "date": pd.to_datetime(df["datetime"], errors="coerce"),
        "season": _to_int_season(df["season"]),
        "home_team": df["home_team"].astype(str),
        "away_team": df["away_team"].astype(str),
        "home_state": df["home_team_state"].astype(str),
        "away_state": df["away_team_state"].astype(str),
        "home_goal": _to_int_goals(df["home_goal"]),
        "away_goal": _to_int_goals(df["away_goal"]),
        "round": df["round"].astype(str),
        "stage": pd.NA,
    })
    return out


def _load_copa_do_brasil(data_dir: str) -> pd.DataFrame:
    df = pd.read_csv(os.path.join(data_dir, "Brazilian_Cup_Matches.csv"))
    out = pd.DataFrame({
        "source": "Brazilian_Cup_Matches.csv",
        "competition": COMP_COPA_DO_BRASIL,
        "competition_raw": COMP_COPA_DO_BRASIL,
        "date": pd.to_datetime(df["datetime"], errors="coerce"),
        "season": _to_int_season(df["season"]),
        "home_team": df["home_team"].astype(str),
        "away_team": df["away_team"].astype(str),
        "home_state": pd.NA,
        "away_state": pd.NA,
        "home_goal": _to_int_goals(df["home_goal"]),
        "away_goal": _to_int_goals(df["away_goal"]),
        "round": df["round"].astype(str),
        "stage": pd.NA,
    })
    return out


def _load_libertadores(data_dir: str) -> pd.DataFrame:
    df = pd.read_csv(os.path.join(data_dir, "Libertadores_Matches.csv"))
    out = pd.DataFrame({
        "source": "Libertadores_Matches.csv",
        "competition": COMP_LIBERTADORES,
        "competition_raw": COMP_LIBERTADORES,
        "date": pd.to_datetime(df["datetime"], errors="coerce"),
        "season": _to_int_season(df["season"]),
        "home_team": df["home_team"].astype(str),
        "away_team": df["away_team"].astype(str),
        "home_state": pd.NA,
        "away_state": pd.NA,
        "home_goal": _to_int_goals(df["home_goal"]),
        "away_goal": _to_int_goals(df["away_goal"]),
        "round": pd.NA,
        "stage": df["stage"].astype(str),
    })
    return out


def _load_br_football(data_dir: str) -> pd.DataFrame:
    df = pd.read_csv(os.path.join(data_dir, "BR-Football-Dataset.csv"))
    # Combine the separate date + time columns.
    dt_str = df["date"].astype(str) + " " + df["time"].fillna("00:00:00").astype(str)
    dates = pd.to_datetime(dt_str, errors="coerce")

    # Map the raw tournament labels to canonical competitions.
    tour_map = {
        "Copa do Brasil": COMP_COPA_DO_BRASIL,
        "Serie A": COMP_BRASILEIRAO,
        "Serie B": COMP_SERIE_B,
        "Serie C": COMP_SERIE_C,
    }
    comp = df["tournament"].astype(str).map(tour_map).fillna(df["tournament"].astype(str))

    out = pd.DataFrame({
        "source": "BR-Football-Dataset.csv",
        "competition": comp,
        "competition_raw": df["tournament"].astype(str),
        "date": dates,
        # Season is not present in this file; use the calendar year of the
        # match date as a season proxy (Brazilian seasons follow the calendar year).
        "season": dates.dt.year.astype("Int64"),
        "home_team": df["home"].astype(str),
        "away_team": df["away"].astype(str),
        "home_state": pd.NA,
        "away_state": pd.NA,
        "home_goal": _to_int_goals(df["home_goal"]),
        "away_goal": _to_int_goals(df["away_goal"]),
        "round": pd.NA,
        "stage": pd.NA,
        "home_corners": _to_int_goals(df["home_corner"]),
        "away_corners": _to_int_goals(df["away_corner"]),
        "home_shots": _to_int_goals(df["home_shots"]),
        "away_shots": _to_int_goals(df["away_shots"]),
        "home_attacks": _to_int_goals(df["home_attack"]),
        "away_attacks": _to_int_goals(df["away_attack"]),
        "total_corners": _to_int_goals(df["total_corners"]),
    })
    return out


def _load_novo(data_dir: str) -> pd.DataFrame:
    df = pd.read_csv(os.path.join(data_dir, "novo_campeonato_brasileiro.csv"))
    out = pd.DataFrame({
        "source": "novo_campeonato_brasileiro.csv",
        "competition": COMP_BRASILEIRAO,
        "competition_raw": "Campeonato Brasileiro",
        "date": pd.to_datetime(df["Data"], format="%d/%m/%Y", errors="coerce"),
        "season": _to_int_season(df["Ano"]),
        "home_team": df["Equipe_mandante"].astype(str),
        "away_team": df["Equipe_visitante"].astype(str),
        "home_state": df["Mandante_UF"].astype(str),
        "away_state": df["Visitante_UF"].astype(str),
        "home_goal": _to_int_goals(df["Gols_mandante"]),
        "away_goal": _to_int_goals(df["Gols_visitante"]),
        "round": df["Rodada"].astype(str),
        "stage": pd.NA,
        "arena": df["Arena"].astype(str),
    })
    return out


def _load_players(data_dir: str) -> pd.DataFrame:
    # The file ships with a UTF-8 BOM and a leading unnamed index column.
    df = pd.read_csv(
        os.path.join(data_dir, "fifa_data.csv"),
        encoding="utf-8-sig",
        index_col=0,
    )
    # Keep only the columns that matter for the player query capabilities and
    # drop the heavy URL columns to keep memory/printing tidy.
    keep = [
        "ID", "Name", "Age", "Nationality", "Overall", "Potential", "Club",
        "Position", "Jersey Number", "Height", "Weight",
        "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
        "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
        "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
        "ShotPower", "Jumping", "Stamina", "Strength", "LongShots",
        "Aggression", "Interceptions", "Positioning", "Vision", "Penalties",
        "Composure", "Preferred Foot", "Work Rate", "Value", "Wage",
    ]
    cols = [c for c in keep if c in df.columns]
    players = df[cols].copy()
    players["Overall"] = pd.to_numeric(players["Overall"], errors="coerce")
    players["Potential"] = pd.to_numeric(players["Potential"], errors="coerce")
    players["Age"] = pd.to_numeric(players["Age"], errors="coerce")
    players["Club_norm"] = players["Club"].map(normalize_team)
    players["Nationality_norm"] = players["Nationality"].map(normalize_team)
    return players


# ---------------------------------------------------------------------------
# DataStore: a cached, lazily-loaded bundle of the normalized data
# ---------------------------------------------------------------------------

class DataStore:
    """Holds the normalized matches and players DataFrames plus lookups."""

    def __init__(self, data_dir: Optional[str] = None) -> None:
        self.data_dir = data_dir or _DEFAULT_DATA_DIR
        self.matches: pd.DataFrame = self._load_matches(self.data_dir)
        self.players: pd.DataFrame = _load_players(self.data_dir)
        # Pre-compute normalized team keys for fast filtering.
        self.matches["home_team_norm"] = self.matches["home_team"].map(normalize_team)
        self.matches["away_team_norm"] = self.matches["away_team"].map(normalize_team)
        # Re-order columns so the important ones come first.
        front = [
            "source", "competition", "competition_raw", "date", "season",
            "home_team", "away_team", "home_team_norm", "away_team_norm",
            "home_goal", "away_goal", "round", "stage",
        ]
        self.matches = self.matches[
            [c for c in front if c in self.matches.columns]
            + [c for c in self.matches.columns if c not in front]
        ]

    @staticmethod
    def _load_matches(data_dir: str) -> pd.DataFrame:
        frames = [
            _load_brasileirao(data_dir),
            _load_copa_do_brasil(data_dir),
            _load_libertadores(data_dir),
            _load_br_football(data_dir),
            _load_novo(data_dir),
        ]
        matches = pd.concat(frames, ignore_index=True, sort=False)
        # Sort by date (NaT last) for stable, predictable output.
        matches = matches.sort_values(
            by="date", kind="mergesort", na_position="last"
        ).reset_index(drop=True)
        return matches

    # -- convenience accessors ------------------------------------------------
    def competitions(self) -> list[str]:
        return sorted(self.matches["competition"].dropna().unique().tolist())

    def seasons(self, competition: Optional[str] = None) -> list[int]:
        sub = self.matches
        if competition:
            sub = sub[sub["competition"] == canonical_competition(competition)]
        return sorted(
            int(s) for s in sub["season"].dropna().unique().tolist()
        )

    def teams(self, competition: Optional[str] = None) -> list[str]:
        sub = self.matches
        if competition:
            sub = sub[sub["competition"] == canonical_competition(competition)]
        names = pd.concat([sub["home_team"], sub["away_team"]], ignore_index=True)
        # Dedupe preserving the most common spelling for display.
        return sorted(n for n in names.dropna().unique().tolist() if n)


@lru_cache(maxsize=1)
def get_store(data_dir: Optional[str] = None) -> DataStore:
    """Return a process-wide cached ``DataStore`` (loaded once)."""
    return DataStore(data_dir=data_dir)
