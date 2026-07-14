"""
Context
=======
Module: brazilian_soccer_mcp.loader
Purpose: Read the six provided Kaggle CSVs and project them into two normalized
         in-memory pandas tables: a unified ``matches`` frame and a ``players``
         frame. All team names are canonicalized via :mod:`.normalize` so that
         cross-source queries (head-to-head, standings) are consistent.

Unified match schema (one row per match)
----------------------------------------
    date         datetime64  -- kickoff date (time dropped; multiple input formats)
    season       int         -- competition year
    competition  str         -- canonical competition name (see _COMP_*)
    home_raw     str         -- original home name (for display)
    away_raw     str
    home_key     str         -- normalized lookup key (suffix-stripped, deaccented)
    away_key     str
    home_state   str|None    -- state/country token when present
    away_state   str|None
    home_goal    int
    away_goal    int
    stage        str|None    -- round/stage label for display
    home_shots   float       -- extended stats (BR-Football only; else NaN)
    away_shots   float
    home_corner  float
    away_corner  float
    source       str         -- originating CSV basename

Source partitioning (instead of cross-source dedup)
----------------------------------------------------
Three sources overlap on Brasileirão Série A (Brasileirao_Matches 2012-2022,
novo_campeonato 2003-2019, BR-Football "Serie A"), but they spell the same club
irreconcilably differently ("Vasco" / "Vasco da Gama RJ", "Athletico" /
"Atlético Paranaense"), so the same fixture gets different normalized keys and
row-level dedup cannot collapse it. Instead each ``(competition, season)`` slice
is sourced from exactly ONE CSV — the highest-priority one present (see
``_SOURCE_PRIORITY``) — guaranteeing clean, non-double-counted round-robin
standings and head-to-head records. A final intra-source key dedup removes any
accidental repeats within a single file.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .normalize import base_key, split_suffix, team_key

# Canonical competition labels.
_COMP_SERIE_A = "Brasileirão Série A"
_COMP_SERIE_B = "Brasileirão Série B"
_COMP_SERIE_C = "Brasileirão Série C"
_COMP_COPA_BR = "Copa do Brasil"
_COMP_LIBERTADORES = "Copa Libertadores"

_BR_FOOTBALL_TOURNAMENT = {
    "Serie A": _COMP_SERIE_A,
    "Serie B": _COMP_SERIE_B,
    "Serie C": _COMP_SERIE_C,
    "Copa do Brasil": _COMP_COPA_BR,
}

_MATCH_COLUMNS = [
    "date", "season", "competition",
    "home_raw", "away_raw", "home_key", "away_key", "home_id", "away_id",
    "home_state", "away_state", "home_goal", "away_goal",
    "stage", "home_shots", "away_shots", "home_corner", "away_corner",
    "source",
]


def _key_series(raw: pd.Series) -> pd.Series:
    """Vectorized ``base_key`` (state-stripped) over a name column, computing each
    distinct raw string only once."""
    uniques = raw.dropna().unique()
    table = {u: base_key(u) for u in uniques}
    return raw.map(table)


def _id_series(raw: pd.Series) -> pd.Series:
    """Vectorized ``team_key`` (state-aware identity) over a name column."""
    uniques = raw.dropna().unique()
    table = {u: team_key(u) for u in uniques}
    return raw.map(table)


def _state_series(raw: pd.Series) -> pd.Series:
    uniques = raw.dropna().unique()
    table = {u: split_suffix(u)[1] for u in uniques}
    return raw.map(table)


def _finalize(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """Coerce goals to int, drop rows lacking a result, add normalized keys and
    any missing optional columns, and stamp the source."""
    df = df.copy()
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    df = df.dropna(subset=["home_goal", "away_goal", "home_raw", "away_raw"])
    df["home_goal"] = df["home_goal"].astype(int)
    df["away_goal"] = df["away_goal"].astype(int)
    df["home_key"] = _key_series(df["home_raw"])
    df["away_key"] = _key_series(df["away_raw"])
    df["home_id"] = _id_series(df["home_raw"])
    df["away_id"] = _id_series(df["away_raw"])
    df["home_state"] = _state_series(df["home_raw"])
    df["away_state"] = _state_series(df["away_raw"])
    df["source"] = source
    for col in ("stage", "home_shots", "away_shots", "home_corner", "away_corner"):
        if col not in df.columns:
            df[col] = pd.NA
    df["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["season"])
    df["season"] = df["season"].astype(int)
    return df[_MATCH_COLUMNS]


def _load_brasileirao(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    out = pd.DataFrame({
        "date": pd.to_datetime(df["datetime"], errors="coerce"),
        "season": df["season"],
        "competition": _COMP_SERIE_A,
        "home_raw": df["home_team"],
        "away_raw": df["away_team"],
        "home_goal": df["home_goal"],
        "away_goal": df["away_goal"],
        "stage": "Round " + df["round"].astype(str),
    })
    return _finalize(out, "Brasileirao_Matches.csv")


def _load_cup(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    out = pd.DataFrame({
        "date": pd.to_datetime(df["datetime"], errors="coerce"),
        "season": df["season"],
        "competition": _COMP_COPA_BR,
        "home_raw": df["home_team"],
        "away_raw": df["away_team"],
        "home_goal": df["home_goal"],
        "away_goal": df["away_goal"],
        "stage": df["round"].astype(str),
    })
    return _finalize(out, "Brazilian_Cup_Matches.csv")


def _load_libertadores(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    out = pd.DataFrame({
        "date": pd.to_datetime(df["datetime"], errors="coerce"),
        "season": df["season"],
        "competition": _COMP_LIBERTADORES,
        "home_raw": df["home_team"],
        "away_raw": df["away_team"],
        "home_goal": df["home_goal"],
        "away_goal": df["away_goal"],
        "stage": df["stage"],
    })
    return _finalize(out, "Libertadores_Matches.csv")


def _load_novo(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    out = pd.DataFrame({
        "date": pd.to_datetime(df["Data"], format="%d/%m/%Y", errors="coerce"),
        "season": df["Ano"],
        "competition": _COMP_SERIE_A,
        "home_raw": df["Equipe_mandante"],
        "away_raw": df["Equipe_visitante"],
        "home_goal": df["Gols_mandante"],
        "away_goal": df["Gols_visitante"],
        "stage": "Round " + df["Rodada"].astype(str),
    })
    return _finalize(out, "novo_campeonato_brasileiro.csv")


def _load_br_football(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    date = pd.to_datetime(df["date"], errors="coerce")
    out = pd.DataFrame({
        "date": date,
        "season": date.dt.year,
        "competition": df["tournament"].map(_BR_FOOTBALL_TOURNAMENT),
        "home_raw": df["home"],
        "away_raw": df["away"],
        "home_goal": df["home_goal"],
        "away_goal": df["away_goal"],
        "stage": pd.NA,
        "home_shots": df.get("home_shots"),
        "away_shots": df.get("away_shots"),
        "home_corner": df.get("home_corner"),
        "away_corner": df.get("away_corner"),
    })
    out = out.dropna(subset=["competition"])
    return _finalize(out, "BR-Football-Dataset.csv")


# Per-source priority. For any (competition, season) slice covered by more than
# one CSV we keep exactly ONE source — the lowest-priority number present —
# because the three Série A sources spell teams irreconcilably differently
# ("Vasco" vs "Vasco da Gama RJ", "Athletico" vs "Atlético Paranaense"), so
# key-based row dedup across sources cannot collapse the same fixture. Choosing
# a single source per slice guarantees clean round-robin standings/H2H.
_SOURCE_PRIORITY = {
    "Brasileirao_Matches.csv": 1,       # Série A 2012-2022, round-annotated
    "Brazilian_Cup_Matches.csv": 1,     # Copa do Brasil 2012-2021
    "Libertadores_Matches.csv": 1,      # Libertadores 2013-2022
    "novo_campeonato_brasileiro.csv": 2,  # Série A 2003-2019 (historical fill)
    "BR-Football-Dataset.csv": 3,       # fallback; sole source for Série B/C & 2023
}


def load_matches(data_dir: Path) -> pd.DataFrame:
    """Load and unify all match CSVs into a single non-overlapping frame.

    Each (competition, season) is sourced from exactly one CSV (the highest
    priority present), so no cross-source duplicate fixtures can occur. A final
    intra-source dedup on normalized keys drops any accidental repeats within a
    single file.
    """
    frames = [
        _load_brasileirao(data_dir / "Brasileirao_Matches.csv"),
        _load_novo(data_dir / "novo_campeonato_brasileiro.csv"),
        _load_cup(data_dir / "Brazilian_Cup_Matches.csv"),
        _load_libertadores(data_dir / "Libertadores_Matches.csv"),
        _load_br_football(data_dir / "BR-Football-Dataset.csv"),
    ]
    matches = pd.concat(frames, ignore_index=True)
    matches["_prio"] = matches["source"].map(_SOURCE_PRIORITY)
    best = matches.groupby(["competition", "season"])["_prio"].transform("min")
    matches = matches[matches["_prio"] == best]
    matches = matches.drop_duplicates(
        subset=["competition", "season", "home_id", "away_id"],
        keep="first",
    ).drop(columns="_prio").reset_index(drop=True)
    return matches


def load_players(data_dir: Path) -> pd.DataFrame:
    """Load the FIFA player database, retaining display + filter columns and a
    normalized club key for cross-file club matching."""
    df = pd.read_csv(data_dir / "fifa_data.csv")
    cols = ["Name", "Age", "Nationality", "Overall", "Potential",
            "Club", "Position", "Jersey Number", "Height", "Weight"]
    keep = [c for c in cols if c in df.columns]
    players = df[keep].copy()
    players["club_key"] = _key_series(players["Club"].fillna(""))
    players["name_lower"] = players["Name"].fillna("").str.lower()
    return players
