"""
Data loading and normalization for Brazilian Soccer MCP Server.

Loads all 6 CSV files from data/kaggle/ and provides a unified interface.
Team names are normalized for consistent matching across datasets.
"""

import re
import unicodedata
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).parent / "data" / "kaggle"


def strip_accents(s: str) -> str:
    """Remove Unicode accent marks from a string."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


def normalize_team(name) -> str:
    """
    Normalize a team name for consistent cross-dataset matching.

    - Strips state suffixes: "Palmeiras-SP" → "palmeiras"
    - Strips country suffixes: "Nacional (URU)" → "nacional"
    - Removes parenthetical old names: "Boavista (antigo EC Barreira) - RJ" → "boavista"
    - Strips accents: "Grêmio" → "gremio"
    - Lowercases
    """
    if name is None or (isinstance(name, float) and np.isnan(name)):
        return ""
    name = str(name).strip()
    # Remove parenthetical expressions at end
    name = re.sub(r"\s*\([^)]+\)\s*$", "", name)
    # Remove parenthetical expressions in middle (e.g. "Boavista Sport Club (antigo EC Barreira) - RJ")
    name = re.sub(r"\s*\([^)]+\)", "", name)
    # Remove trailing state/country suffix: -SP, -RJ, -URU, -EQU, etc.
    name = re.sub(r"\s*-\s*[A-Za-z]{2,3}\s*$", "", name)
    name = name.strip()
    return strip_accents(name.lower())


def parse_date(date_str) -> Optional[str]:
    """
    Parse various date formats to ISO date string (YYYY-MM-DD).

    Handles:
    - "2023-09-24 18:30:00" → "2023-09-24"
    - "2023-09-24" → "2023-09-24"
    - "29/03/2003" → "2003-03-29"
    """
    if date_str is None or (isinstance(date_str, float) and np.isnan(date_str)):
        return None
    date_str = str(date_str).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%Y %H:%M"):
        try:
            return pd.to_datetime(date_str, format=fmt).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            pass
    try:
        return pd.to_datetime(date_str, dayfirst=False).strftime("%Y-%m-%d")
    except Exception:
        return date_str


def _extract_year(date_str) -> int:
    """Extract year from a date string."""
    if date_str is None or (isinstance(date_str, float) and np.isnan(date_str)):
        return 0
    s = str(date_str).strip()
    if len(s) >= 4:
        try:
            return int(s[:4])
        except ValueError:
            pass
    return 0


def _make_match_row(
    date, home_raw, away_raw, home_goal, away_goal,
    competition, season, round_val, stage, source
) -> dict:
    return {
        "date": date,
        "home_team_raw": home_raw,
        "away_team_raw": away_raw,
        "home_team": normalize_team(home_raw),
        "away_team": normalize_team(away_raw),
        "home_goal": home_goal,
        "away_goal": away_goal,
        "competition": competition,
        "season": season,
        "round": round_val,
        "stage": stage,
        "source": source,
    }


def _to_int(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0).astype(int)


class SoccerDataLoader:
    """Loads and caches all Brazilian soccer CSV data."""

    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir
        self._matches: Optional[pd.DataFrame] = None
        self._players: Optional[pd.DataFrame] = None

    # ------------------------------------------------------------------ #
    # Private loaders                                                      #
    # ------------------------------------------------------------------ #

    def _load_brasileirao(self) -> pd.DataFrame:
        df = pd.read_csv(
            self.data_dir / "Brasileirao_Matches.csv",
            encoding="utf-8",
            dtype=str,
        )
        return pd.DataFrame(
            {
                "date": df["datetime"].apply(parse_date),
                "home_team_raw": df["home_team"],
                "away_team_raw": df["away_team"],
                "home_team": df["home_team"].apply(normalize_team),
                "away_team": df["away_team"].apply(normalize_team),
                "home_goal": _to_int(df["home_goal"]),
                "away_goal": _to_int(df["away_goal"]),
                "competition": "Brasileirão",
                "season": _to_int(df["season"]),
                "round": df["round"].fillna(""),
                "stage": "",
                "source": "brasileirao",
            }
        )

    def _load_copa_brasil(self) -> pd.DataFrame:
        df = pd.read_csv(
            self.data_dir / "Brazilian_Cup_Matches.csv",
            encoding="utf-8",
            dtype=str,
        )
        return pd.DataFrame(
            {
                "date": df["datetime"].apply(parse_date),
                "home_team_raw": df["home_team"],
                "away_team_raw": df["away_team"],
                "home_team": df["home_team"].apply(normalize_team),
                "away_team": df["away_team"].apply(normalize_team),
                "home_goal": _to_int(df["home_goal"]),
                "away_goal": _to_int(df["away_goal"]),
                "competition": "Copa do Brasil",
                "season": _to_int(df["season"]),
                "round": df["round"].fillna(""),
                "stage": "",
                "source": "copa_brasil",
            }
        )

    def _load_libertadores(self) -> pd.DataFrame:
        df = pd.read_csv(
            self.data_dir / "Libertadores_Matches.csv",
            encoding="utf-8",
            dtype=str,
        )
        return pd.DataFrame(
            {
                "date": df["datetime"].apply(parse_date),
                "home_team_raw": df["home_team"],
                "away_team_raw": df["away_team"],
                "home_team": df["home_team"].apply(normalize_team),
                "away_team": df["away_team"].apply(normalize_team),
                "home_goal": _to_int(df["home_goal"]),
                "away_goal": _to_int(df["away_goal"]),
                "competition": "Copa Libertadores",
                "season": _to_int(df["season"]),
                "round": "",
                "stage": df["stage"].fillna(""),
                "source": "libertadores",
            }
        )

    def _load_br_football(self) -> pd.DataFrame:
        df = pd.read_csv(
            self.data_dir / "BR-Football-Dataset.csv",
            encoding="utf-8",
            dtype=str,
        )
        return pd.DataFrame(
            {
                "date": df["date"].apply(parse_date),
                "home_team_raw": df["home"],
                "away_team_raw": df["away"],
                "home_team": df["home"].apply(normalize_team),
                "away_team": df["away"].apply(normalize_team),
                "home_goal": _to_int(df["home_goal"]),
                "away_goal": _to_int(df["away_goal"]),
                "competition": df["tournament"].fillna("Unknown"),
                "season": df["date"].apply(_extract_year),
                "round": "",
                "stage": "",
                "source": "br_football",
            }
        )

    def _load_novo_brasileirao(self) -> pd.DataFrame:
        df = pd.read_csv(
            self.data_dir / "novo_campeonato_brasileiro.csv",
            encoding="utf-8",
            dtype=str,
        )
        return pd.DataFrame(
            {
                "date": df["Data"].apply(parse_date),
                "home_team_raw": df["Equipe_mandante"],
                "away_team_raw": df["Equipe_visitante"],
                "home_team": df["Equipe_mandante"].apply(normalize_team),
                "away_team": df["Equipe_visitante"].apply(normalize_team),
                "home_goal": _to_int(df["Gols_mandante"]),
                "away_goal": _to_int(df["Gols_visitante"]),
                "competition": "Brasileirão",
                "season": _to_int(df["Ano"]),
                "round": df["Rodada"].fillna(""),
                "stage": "",
                "source": "novo_brasileirao",
            }
        )

    # ------------------------------------------------------------------ #
    # Public properties (lazy-loaded, cached)                             #
    # ------------------------------------------------------------------ #

    @property
    def matches(self) -> pd.DataFrame:
        """Unified DataFrame of all matches from all sources."""
        if self._matches is None:
            frames = [
                self._load_brasileirao(),
                self._load_copa_brasil(),
                self._load_libertadores(),
                self._load_br_football(),
                self._load_novo_brasileirao(),
            ]
            df = pd.concat(frames, ignore_index=True)
            # Drop rows with empty team names
            df = df[
                (df["home_team"] != "") & (df["away_team"] != "")
            ].reset_index(drop=True)
            self._matches = df
        return self._matches

    @property
    def players(self) -> pd.DataFrame:
        """FIFA player data."""
        if self._players is None:
            # utf-8-sig strips the BOM from the first column header
            df = pd.read_csv(
                self.data_dir / "fifa_data.csv",
                encoding="utf-8-sig",
                dtype=str,
            )
            df.columns = df.columns.str.strip()
            self._players = df
        return self._players

    def find_matching_team_name(self, query: str) -> list[str]:
        """Return raw team names that match the normalized query."""
        norm = normalize_team(query)
        df = self.matches
        home = df[df["home_team"].str.contains(norm, na=False)]["home_team_raw"]
        away = df[df["away_team"].str.contains(norm, na=False)]["away_team_raw"]
        names = pd.concat([home, away]).dropna().unique()
        return sorted(names)
