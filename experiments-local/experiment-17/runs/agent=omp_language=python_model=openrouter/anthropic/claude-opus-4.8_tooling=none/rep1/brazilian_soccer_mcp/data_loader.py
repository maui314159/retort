"""
Context
=======
Module: brazilian_soccer_mcp.data_loader

Loads the six Kaggle CSVs in `data/kaggle/` and folds them into two tidy,
query-ready pandas frames held by a `KnowledgeBase`:

  * `matches`  - one row per match, unified schema regardless of source file.
  * `players`  - the FIFA player table, lightly cleaned.

Why a unified match frame?
--------------------------
The five match files disagree on column names, ordering, dtypes and even
which competition a row belongs to:

  - Brasileirao_Matches.csv      home_team/away_team, goals as int, has state.
  - Brazilian_Cup_Matches.csv    team names carry " - MG" style suffixes.
  - Libertadores_Matches.csv     goals stored as *quoted strings*, has stage,
                                 plus 2 rows with missing goals/date.
  - BR-Football-Dataset.csv      column order home,home_goal,away_goal,away;
                                 goals are floats; tournament in {Serie A/B/C,
                                 Copa do Brasil}; no season column (derive from
                                 date); rich stats (shots, corners).
  - novo_campeonato_brasileiro   Portuguese columns, DD/MM/YYYY dates, 2003-19.

We map every source onto a single set of logical competitions
("Brasileirão Série A/B/C", "Copa do Brasil", "Copa Libertadores") and then
**deduplicate** on (competition, season, home_canon, away_canon). That last
step matters: Série A 2012-2019 appears in *three* files, so without dedup
every standings/average query would triple-count those seasons. When
duplicates collide we keep the most complete row (goals present, then extra
stats present, then a round label).

Canonical name keys (`home_canon`, `away_canon`) are computed once here so
query-time matching is a cheap string compare rather than re-normalising
thousands of rows per call.

Loading is process-cached (`get_knowledge_base`) - the CSVs total ~25k rows
and parse in well under a second, comfortably inside the spec's latency
budget once cached.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pandas as pd

from .normalize import canonical, parse_date, strip_affixes

# --- competition labels -----------------------------------------------------
SERIE_A = "Brasileirão Série A"
SERIE_B = "Brasileirão Série B"
SERIE_C = "Brasileirão Série C"
COPA_BR = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"

# BR-Football-Dataset `tournament` values -> logical competition.
_BR_TOURNAMENT_MAP = {
    "Serie A": SERIE_A,
    "Serie B": SERIE_B,
    "Serie C": SERIE_C,
    "Copa do Brasil": COPA_BR,
}

# Unified match schema. Every per-file reader emits exactly these columns.
_MATCH_COLUMNS = [
    "competition",
    "season",
    "round",
    "stage",
    "match_date",
    "home",
    "away",
    "home_canon",
    "away_canon",
    "home_goal",
    "away_goal",
    "home_shots",
    "away_shots",
    "home_corner",
    "away_corner",
    "source",
]


def default_data_dir() -> Path:
    """Locate `data/kaggle`, honouring the BR_SOCCER_DATA_DIR override.

    Resolution order:
      1. $BR_SOCCER_DATA_DIR if set.
      2. <cwd>/data/kaggle (the layout shipped with this repo).
      3. <repo-root>/data/kaggle relative to this file.
    The first existing directory wins; otherwise option 2 is returned so the
    eventual error message points at the conventional location.
    """
    env = os.environ.get("BR_SOCCER_DATA_DIR")
    if env:
        return Path(env)
    cwd_candidate = Path.cwd() / "data" / "kaggle"
    if cwd_candidate.is_dir():
        return cwd_candidate
    repo_candidate = Path(__file__).resolve().parent.parent / "data" / "kaggle"
    if repo_candidate.is_dir():
        return repo_candidate
    return cwd_candidate


def _to_int(series: pd.Series) -> pd.Series:
    """Coerce a column of mixed str/float goal counts to nullable Int64."""
    return pd.to_numeric(series, errors="coerce").astype("Int64")


def _add_canon(df: pd.DataFrame) -> pd.DataFrame:
    """Attach display + canonical name columns from raw home/away strings."""
    df["home"] = df["home_raw"].map(strip_affixes)
    df["away"] = df["away_raw"].map(strip_affixes)
    df["home_canon"] = df["home_raw"].map(canonical)
    df["away_canon"] = df["away_raw"].map(canonical)
    return df


def _finalize(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure every unified column exists (fill missing with NA) and order."""
    for col in _MATCH_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    return df[_MATCH_COLUMNS]


def _read_brasileirao(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path)
    df = pd.DataFrame()
    df["home_raw"] = raw["home_team"]
    df["away_raw"] = raw["away_team"]
    df = _add_canon(df)
    df["competition"] = SERIE_A
    df["season"] = _to_int(raw["season"])
    df["round"] = raw["round"].astype("string")
    df["match_date"] = raw["datetime"].map(parse_date)
    df["home_goal"] = _to_int(raw["home_goal"])
    df["away_goal"] = _to_int(raw["away_goal"])
    df["source"] = path.name
    return _finalize(df)


def _read_cup(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path)
    df = pd.DataFrame()
    df["home_raw"] = raw["home_team"]
    df["away_raw"] = raw["away_team"]
    df = _add_canon(df)
    df["competition"] = COPA_BR
    df["season"] = _to_int(raw["season"])
    df["round"] = raw["round"].astype("string")
    df["match_date"] = raw["datetime"].map(parse_date)
    df["home_goal"] = _to_int(raw["home_goal"])
    df["away_goal"] = _to_int(raw["away_goal"])
    df["source"] = path.name
    return _finalize(df)


def _read_libertadores(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path)
    df = pd.DataFrame()
    df["home_raw"] = raw["home_team"]
    df["away_raw"] = raw["away_team"]
    df = _add_canon(df)
    df["competition"] = LIBERTADORES
    df["season"] = _to_int(raw["season"])
    df["stage"] = raw["stage"].astype("string")
    df["match_date"] = raw["datetime"].map(parse_date)
    df["home_goal"] = _to_int(raw["home_goal"])
    df["away_goal"] = _to_int(raw["away_goal"])
    df["source"] = path.name
    return _finalize(df)


def _read_br_football(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path)
    df = pd.DataFrame()
    df["home_raw"] = raw["home"]
    df["away_raw"] = raw["away"]
    df = _add_canon(df)
    df["competition"] = raw["tournament"].map(_BR_TOURNAMENT_MAP)
    df["match_date"] = raw["date"].map(parse_date)
    # No season column: derive from the parsed date's year.
    df["season"] = pd.array(
        [d.year if d is not None else pd.NA for d in df["match_date"]],
        dtype="Int64",
    )
    df["home_goal"] = _to_int(raw["home_goal"])
    df["away_goal"] = _to_int(raw["away_goal"])
    df["home_shots"] = pd.to_numeric(raw["home_shots"], errors="coerce")
    df["away_shots"] = pd.to_numeric(raw["away_shots"], errors="coerce")
    df["home_corner"] = pd.to_numeric(raw["home_corner"], errors="coerce")
    df["away_corner"] = pd.to_numeric(raw["away_corner"], errors="coerce")
    df["source"] = path.name
    # Drop rows whose tournament didn't map to a known competition.
    df = df[df["competition"].notna()]
    return _finalize(df)


def _read_novo(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path)
    df = pd.DataFrame()
    df["home_raw"] = raw["Equipe_mandante"]
    df["away_raw"] = raw["Equipe_visitante"]
    df = _add_canon(df)
    df["competition"] = SERIE_A
    df["season"] = _to_int(raw["Ano"])
    df["round"] = raw["Rodada"].astype("string")
    df["match_date"] = raw["Data"].map(parse_date)
    df["home_goal"] = _to_int(raw["Gols_mandante"])
    df["away_goal"] = _to_int(raw["Gols_visitante"])
    df["source"] = path.name
    return _finalize(df)


def _read_players(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path)
    # The first column is an unnamed export index; drop it if present.
    if raw.columns[0].strip("\ufeff") == "" or raw.columns[0] == "Unnamed: 0":
        raw = raw.drop(columns=raw.columns[0])
    keep = [
        "ID",
        "Name",
        "Age",
        "Nationality",
        "Overall",
        "Potential",
        "Club",
        "Position",
        "Jersey Number",
        "Height",
        "Weight",
        "Value",
        "Wage",
        "Preferred Foot",
    ]
    present = [c for c in keep if c in raw.columns]
    players = raw[present].copy()
    players["Name"] = players["Name"].astype("string").fillna("")
    players["Nationality"] = players["Nationality"].astype("string").fillna("")
    players["Club"] = players["Club"].astype("string").fillna("")
    players["Position"] = players["Position"].astype("string").fillna("")
    players["Overall"] = pd.to_numeric(players["Overall"], errors="coerce")
    # Precompute match keys for fast name/club/nationality lookups.
    players["name_canon"] = players["Name"].map(canonical)
    players["club_canon"] = players["Club"].map(canonical)
    players["nationality_canon"] = players["Nationality"].map(canonical)
    return players


@dataclass
class KnowledgeBase:
    """In-memory store of unified matches + players, with source metadata."""

    matches: pd.DataFrame
    players: pd.DataFrame
    data_dir: Path

    @property
    def competitions(self) -> list[str]:
        return sorted(self.matches["competition"].dropna().unique().tolist())

    @property
    def seasons(self) -> list[int]:
        return sorted(int(s) for s in self.matches["season"].dropna().unique())


# Completeness score for dedup: prefer rows that have goals, then stats,
# then a round/stage label. Higher score = kept.
def _completeness(df: pd.DataFrame) -> pd.Series:
    score = pd.Series(0, index=df.index, dtype="int64")
    score += df["home_goal"].notna().astype("int64") * 4
    score += df["home_shots"].notna().astype("int64") * 2
    score += df["round"].notna().astype("int64")
    score += df["stage"].notna().astype("int64")
    return score


def build_knowledge_base(data_dir: str | os.PathLike | None = None) -> KnowledgeBase:
    """Read every CSV, unify, dedup, and return a `KnowledgeBase`.

    Raises FileNotFoundError listing any missing files so setup problems are
    obvious rather than surfacing as empty query results.
    """
    base = Path(data_dir) if data_dir is not None else default_data_dir()
    readers = {
        "Brasileirao_Matches.csv": _read_brasileirao,
        "Brazilian_Cup_Matches.csv": _read_cup,
        "Libertadores_Matches.csv": _read_libertadores,
        "BR-Football-Dataset.csv": _read_br_football,
        "novo_campeonato_brasileiro.csv": _read_novo,
    }
    missing = [name for name in (*readers, "fifa_data.csv") if not (base / name).is_file()]
    if missing:
        raise FileNotFoundError(
            f"Missing data files in {base}: {', '.join(missing)}. "
            "Set BR_SOCCER_DATA_DIR or run from the repo root."
        )

    frames = [reader(base / name) for name, reader in readers.items()]
    matches = pd.concat(frames, ignore_index=True)

    # Deduplicate logical matches that appear in multiple source files
    # (Série A 2012-2019 lives in 3 files). Keep the most complete row.
    matches["_score"] = _completeness(matches)
    matches = (
        matches.sort_values("_score", ascending=False, kind="stable")
        .drop_duplicates(
            subset=["competition", "season", "home_canon", "away_canon"],
            keep="first",
        )
        .drop(columns="_score")
        .reset_index(drop=True)
    )

    players = _read_players(base / "fifa_data.csv")
    return KnowledgeBase(matches=matches, players=players, data_dir=base)


@lru_cache(maxsize=4)
def get_knowledge_base(data_dir: str | None = None) -> KnowledgeBase:
    """Process-cached accessor. Pass an explicit dir to bypass auto-detect."""
    return build_knowledge_base(data_dir)
