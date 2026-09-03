"""Loaders that turn the six bundled Kaggle CSV files into a unified,
strongly-typed in-memory model.

Public API
----------
* :func:`load_matches`   -> single :class:`pandas.DataFrame` with every match
  from the five match datasets (Brasileirao, Copa do Brasil, Libertadores,
  extended BR-Football statistics, and the historical 2003-2019 Brasileirao).
* :func:`load_players`   -> :class:`pandas.DataFrame` with the FIFA player data.
* :func:`load_extended_stats` -> per-match extended statistics
  (corners/attacks/shots) from the BR-Football-Dataset.
* :func:`load_all`       -> convenience dict bundling the above plus a few
  derived lookups.

All match rows share the same column schema regardless of their origin so the
query engine can treat them uniformly. Team names are run through
:func:`brsl.normalization.normalize_team` so the cross-dataset join key is
consistent.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import pandas as pd

from .normalization import normalize_team

DATA_DIR = os.environ.get("BRSL_DATA_DIR") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "kaggle"
)

MATCH_FILES = {
    "brasileirao": "Brasileirao_Matches.csv",
    "copa_do_brasil": "Brazilian_Cup_Matches.csv",
    "libertadores": "Libertadores_Matches.csv",
    "br_football": "BR-Football-Dataset.csv",
    "historico": "novo_campeonato_brasileiro.csv",
}

PLAYER_FILE = "fifa_data.csv"

COMPETITION_NAMES = {
    "brasileirao": "Brasileirao Serie A",
    "copa_do_brasil": "Copa do Brasil",
    "libertadores": "Copa Libertadores",
    "br_football": None,  # taken per-row from the `tournament` column
    "historico": "Brasileirao Serie A (2003-2019)",
}

# Canonical competition labels used throughout the query engine / MCP tools.
COMPETITION_ALIASES = {
    "brasileirao": ["brasileirao", "brasileirão", "serie a", "série a",
                    "campeonato brasileiro"],
    "copa_do_brasil": ["copa do brasil", "copa do brazil", "brazilian cup",
                       "copa-do-brasil"],
    "libertadores": ["libertadores", "copa libertadores",
                     "libertadores da america"],
}

# Map every competition *label* found in the data to a logical competition
# "bucket" so that the same competition coming from different files (e.g.
# "Brasileirao Serie A" and "Serie A") can be de-duplicated.
COMPETITION_BUCKETS = {
    "Brasileirao Serie A": "brasileirao",
    "Brasileirao Serie A (2003-2019)": "brasileirao",
    "Serie A": "brasileirao",
    "Serie B": "serie_b",
    "Serie C": "serie_c",
    "Copa do Brasil": "copa_do_brasil",
    "Copa Libertadores": "libertadores",
}

# When the same physical match appears in more than one file, prefer the most
# authoritative dedicated source.  Lower index == higher preference.
SOURCE_PREFERENCE = ["copa_do_brasil", "brasileirao", "libertadores",
                     "historico", "br_football"]


def competition_bucket(label: str) -> str | None:
    """Return the logical competition bucket for a raw competition label."""
    if label is None:
        return None
    return COMPETITION_BUCKETS.get(str(label))


def _data_path(filename: str) -> str:
    return os.path.join(DATA_DIR, filename)


def _to_int(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype("Int64")


def _winner(home: pd.Series, away: pd.Series) -> pd.Series:
    out = pd.Series([None] * len(home), dtype="object")
    out[(home > away)] = "home"
    out[(home < away)] = "away"
    out[(home == away) & home.notna()] = "draw"
    return out


def _add_team_columns(df: pd.DataFrame, home_col: str, away_col: str) -> pd.DataFrame:
    home_norm = df[home_col].astype(str).map(normalize_team)
    away_norm = df[away_col].astype(str).map(normalize_team)
    df = df.assign(
        home_team=home_norm.map(lambda t: t.display),
        home_team_key=home_norm.map(lambda t: t.key),
        home_state=home_norm.map(lambda t: t.state),
        away_team=away_norm.map(lambda t: t.display),
        away_team_key=away_norm.map(lambda t: t.key),
        away_state=away_norm.map(lambda t: t.state),
    )
    return df


def _load_brasileirao() -> pd.DataFrame:
    raw = pd.read_csv(_data_path(MATCH_FILES["brasileirao"]))
    df = _add_team_columns(raw, "home_team", "away_team")
    df = df.assign(
        source="brasileirao",
        competition=COMPETITION_NAMES["brasileirao"],
        date=pd.to_datetime(raw["datetime"], errors="coerce"),
        home_goal=_to_int(raw["home_goal"]),
        away_goal=_to_int(raw["away_goal"]),
        season=_to_int(raw["season"]),
        round=raw["round"].astype(str),
        stage=None,
        stadium=None,
    )
    return df


def _load_copa_do_brasil() -> pd.DataFrame:
    raw = pd.read_csv(_data_path(MATCH_FILES["copa_do_brasil"]))
    df = _add_team_columns(raw, "home_team", "away_team")
    df = df.assign(
        source="copa_do_brasil",
        competition=COMPETITION_NAMES["copa_do_brasil"],
        date=pd.to_datetime(raw["datetime"], errors="coerce"),
        home_goal=_to_int(raw["home_goal"]),
        away_goal=_to_int(raw["away_goal"]),
        season=_to_int(raw["season"]),
        round=raw["round"].astype(str),
        stage=None,
        stadium=None,
    )
    return df


def _load_libertadores() -> pd.DataFrame:
    raw = pd.read_csv(_data_path(MATCH_FILES["libertadores"]))
    df = _add_team_columns(raw, "home_team", "away_team")
    df = df.assign(
        source="libertadores",
        competition=COMPETITION_NAMES["libertadores"],
        date=pd.to_datetime(raw["datetime"], errors="coerce"),
        home_goal=_to_int(raw["home_goal"]),
        away_goal=_to_int(raw["away_goal"]),
        season=_to_int(raw["season"]),
        round=None,
        stage=raw["stage"].astype(str),
        stadium=None,
    )
    return df


def _load_br_football() -> pd.DataFrame:
    raw = pd.read_csv(_data_path(MATCH_FILES["br_football"]))
    raw = raw.rename(columns={"home": "_home", "away": "_away"})
    df = _add_team_columns(raw, "_home", "_away")
    date = raw["date"].astype(str)
    time = raw["time"].astype(str)
    dt = pd.to_datetime(date + " " + time, errors="coerce")
    df = df.assign(
        source="br_football",
        competition=raw["tournament"].astype(str),
        date=dt,
        home_goal=_to_int(raw["home_goal"]),
        away_goal=_to_int(raw["away_goal"]),
        season=dt.dt.year.astype("Int64"),
        round=None,
        stage=None,
        stadium=None,
    )
    # carry the extended statistics through as extra columns
    for col in ["home_corner", "away_corner", "home_attack", "away_attack",
                "home_shots", "away_shots", "total_corners", "ht_result",
                "at_result"]:
        if col in raw.columns:
            df[col] = raw[col]
    return df


def _load_historico() -> pd.DataFrame:
    raw = pd.read_csv(_data_path(MATCH_FILES["historico"]))
    df = _add_team_columns(raw, "Equipe_mandante", "Equipe_visitante")
    df = df.assign(
        source="historico",
        competition=COMPETITION_NAMES["historico"],
        date=pd.to_datetime(raw["Data"], format="%d/%m/%Y", errors="coerce"),
        home_goal=_to_int(raw["Gols_mandante"]),
        away_goal=_to_int(raw["Gols_visitante"]),
        season=_to_int(raw["Ano"]),
        round=raw["Rodada"].astype(str),
        stage=None,
        stadium=raw.get("Arena"),
    )
    # The historico file already declares a `Vencedor` column, but we recompute
    # the winner from the scores for consistency with the other datasets.
    return df


_UNIFIED_COLUMNS = [
    "source", "competition", "date", "home_team", "home_team_key", "home_state",
    "away_team", "away_team_key", "away_state", "home_goal", "away_goal",
    "season", "round", "stage", "stadium", "winner",
]

# Optional extended per-match statistics carried only for the BR-Football rows.
EXTENDED_STAT_COLUMNS = [
    "home_corner", "away_corner", "home_attack", "away_attack",
    "home_shots", "away_shots", "total_corners", "ht_result", "at_result",
]


def _finalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["winner"] = _winner(df["home_goal"], df["away_goal"])
    keep = [c for c in _UNIFIED_COLUMNS if c in df.columns]
    extra = [c for c in EXTENDED_STAT_COLUMNS if c in df.columns]
    return df[keep + extra].reset_index(drop=True)


@lru_cache(maxsize=1)
def load_matches() -> pd.DataFrame:
    """Load every match dataset into a single unified DataFrame."""
    frames = [
        _load_brasileirao(),
        _load_copa_do_brasil(),
        _load_libertadores(),
        _load_br_football(),
        _load_historico(),
    ]
    matches = pd.concat(frames, ignore_index=True, sort=False)
    return _finalize(matches)


@lru_cache(maxsize=1)
def load_extended_stats() -> pd.DataFrame:
    """Return the BR-Football rows with their extended statistics intact."""
    return _load_br_football()


@lru_cache(maxsize=1)
def load_matches_deduplicated() -> pd.DataFrame:
    """Return :func:`load_matches` with cross-file duplicate matches removed.

    The same physical match frequently appears in more than one source file
    (for example the 2019 Brasileirao is in both ``Brasileirao_Matches.csv`` and
    ``novo_campeonato_brasileiro.csv``, and the BR-Football-Dataset overlaps
    with all of them).  Duplicate detection keys on
    ``(season, competition-bucket, home-team-key, away-team-key, home-goal,
    away-goal)`` -- deliberately dropping the timestamp, which is recorded at
    different precisions across files -- and keeps the most authoritative
    source per :data:`SOURCE_PREFERENCE`.
    """
    m = load_matches().copy()
    m["_bucket"] = m["competition"].map(competition_bucket)
    m["_rank"] = m["source"].map(lambda s: SOURCE_PREFERENCE.index(s))

    has_goals = (m["home_goal"].notna() & m["away_goal"].notna()
                 & m["season"].notna())
    key_cols = ["_bucket", "season", "home_team_key", "away_team_key",
                "home_goal", "away_goal"]
    valid = m[has_goals].sort_values("_rank")
    deduped = valid.drop_duplicates(subset=key_cols, keep="first")
    nulls = m[~has_goals]
    out = pd.concat([deduped, nulls], ignore_index=True)
    return out.drop(columns=["_bucket", "_rank"]).sort_values(
        "date", kind="stable").reset_index(drop=True)


@lru_cache(maxsize=1)
def load_players() -> pd.DataFrame:
    """Load the FIFA player database."""
    raw = pd.read_csv(_data_path(PLAYER_FILE), encoding="utf-8-sig")
    raw = raw.rename(columns=str.strip)
    # Defensive: a few FIFA exports prepend an unnamed index column.
    if "ID" not in raw.columns and raw.columns[0].startswith("Unnamed"):
        raw = raw.drop(columns=raw.columns[0])
    if "Name" in raw.columns:
        raw["Name"] = raw["Name"].astype(str).str.strip()
    if "Club" in raw.columns:
        raw["Club"] = raw["Club"].astype(str).str.strip()
    if "Nationality" in raw.columns:
        raw["Nationality"] = raw["Nationality"].astype(str).str.strip()
    return raw


def load_all() -> dict[str, pd.DataFrame]:
    """Convenience loader returning ``{"matches": ..., "players": ...}``."""
    return {"matches": load_matches(), "players": load_players()}


def team_lookup() -> dict[str, dict[str, Any]]:
    """Build a {team_key -> {display, states, competitions}} summary."""
    matches = load_matches()
    info: dict[str, dict[str, Any]] = {}
    for side in ("home", "away"):
        for _, row in matches.iterrows():
            key = row[f"{side}_team_key"]
            if not key:
                continue
            entry = info.setdefault(
                key,
                {"display": row[f"{side}_team"], "states": set(),
                 "competitions": set()},
            )
            state = row.get(f"{side}_state")
            if state:
                entry["states"].add(state)
            entry["competitions"].add(row["competition"])
    return info


if __name__ == "__main__":
    m = load_matches()
    print(f"Loaded {len(m)} matches across "
          f"{m['competition'].nunique()} competition labels.")
