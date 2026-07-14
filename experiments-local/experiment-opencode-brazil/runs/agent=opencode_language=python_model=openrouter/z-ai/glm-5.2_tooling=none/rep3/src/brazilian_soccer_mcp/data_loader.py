"""Data loading and normalization for the Brazilian Soccer MCP server.

Context block
-------------
This module is responsible for reading the six Kaggle CSV datasets that ship
in ``data/kaggle/`` and producing normalized, in-memory ``pandas`` structures
that the query layer (``queries.py``) and MCP server (``server.py``) consume.

Responsibilities:
  * Load each CSV with proper encoding (UTF-8) and dtype handling.
  * Normalize team names so that "Palmeiras-SP", "Palmeiras - SP" and
    "Palmeiras" all match the same entity.
  * Parse the multiple date formats present in the datasets (ISO with time,
    ISO date-only and Brazilian DD/MM/YYYY).
  * Produce a single unified ``matches`` DataFrame that combines all five
    match files with a consistent schema, plus a ``players`` DataFrame for
    the FIFA dataset.
"""
from __future__ import annotations

import os
import re
import unicodedata
from datetime import datetime
from functools import lru_cache
from typing import Optional

import pandas as pd

DATA_DIR_ENV = "BRAZILIAN_SOCCER_DATA_DIR"

# Brazilian state abbreviations used to strip the "-UF" suffix from team names.
STATE_ABBREVS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
    "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
    "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}

_PAREN_RE = re.compile(r"\([^)]*\)")
# Matches a trailing "- XX" or "-XX" state suffix (2 uppercase letters).
_STATE_SUFFIX_RE = re.compile(r"\s*-\s*([A-Z]{2})\s*$")


def default_data_dir() -> str:
    """Return the default data directory relative to the project root."""
    env = os.environ.get(DATA_DIR_ENV)
    if env:
        return env
    here = os.path.dirname(os.path.abspath(__file__))
    # src/brazilian_soccer_mcp -> up two levels to project root.
    root = os.path.abspath(os.path.join(here, "..", ".."))
    return os.path.join(root, "data", "kaggle")


def strip_accents(text: str) -> str:
    """Remove diacritics from a string (NFKD decomposition)."""
    if not isinstance(text, str):
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def normalize_team_name(name: object) -> str:
    """Normalize a team name for consistent matching.

    Steps:
      1. Coerce to str, strip.
      2. Remove parenthetical fragments e.g. "(antigo Esporte Clube...)".
      3. Strip a trailing "- UF" state suffix (e.g. "Palmeiras-SP").
      4. Lowercase and remove accents.
      5. Collapse internal whitespace.

    The result is a stable key used for equality comparisons regardless of
    which source file the team name came from.
    """
    if name is None:
        return ""
    s = str(name).strip()
    s = _PAREN_RE.sub("", s).strip()
    # Iteratively strip state suffixes (some names have none).
    while True:
        m = _STATE_SUFFIX_RE.search(s)
        if not m or m.group(1) not in STATE_ABBREVS:
            break
        s = s[: m.start()].strip()
    s = strip_accents(s).lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s


_DISPLAY_CACHE: dict[str, str] = {}


def display_team_name(name: object) -> str:
    """Return a human-friendly display name (strips suffix, keeps accents)."""
    if name is None:
        return ""
    s = str(name).strip()
    s = _PAREN_RE.sub("", s).strip()
    while True:
        m = _STATE_SUFFIX_RE.search(s)
        if not m or m.group(1) not in STATE_ABBREVS:
            break
        s = s[: m.start()].strip()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_date(value: object) -> Optional[datetime]:
    """Parse the multiple date formats present across the datasets.

    Supported formats:
      * ``2012-05-19 18:30:00`` (ISO with time)
      * ``2023-09-24`` (ISO date only)
      * ``29/03/2003`` (Brazilian DD/MM/YYYY)

    Returns ``None`` if the value cannot be parsed.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, datetime):
        return value
    s = str(value).strip()
    if not s:
        return None
    # Try pandas first (handles most ISO variants), then Brazilian format.
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    try:
        return pd.to_datetime(s, errors="coerce").to_pydatetime()
    except Exception:
        return None


def _to_int(value: object) -> Optional[int]:
    """Coerce a goal value to int, returning None when not parseable."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _load_brasileirao(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8")
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "date": parse_date(r.get("datetime")),
            "home_team": str(r.get("home_team")).strip(),
            "away_team": str(r.get("away_team")).strip(),
            "home_team_state": r.get("home_team_state"),
            "away_team_state": r.get("away_team_state"),
            "home_goal": _to_int(r.get("home_goal")),
            "away_goal": _to_int(r.get("away_goal")),
            "season": _to_int(r.get("season")),
            "round": r.get("round"),
            "stage": None,
            "competition": "Brasileirao Serie A",
            "source": "Brasileirao_Matches.csv",
        })
    return pd.DataFrame(rows)


def _load_copa_brasil(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8")
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "date": parse_date(r.get("datetime")),
            "home_team": str(r.get("home_team")).strip(),
            "away_team": str(r.get("away_team")).strip(),
            "home_team_state": None,
            "away_team_state": None,
            "home_goal": _to_int(r.get("home_goal")),
            "away_goal": _to_int(r.get("away_goal")),
            "season": _to_int(r.get("season")),
            "round": r.get("round"),
            "stage": None,
            "competition": "Copa do Brasil",
            "source": "Brazilian_Cup_Matches.csv",
        })
    return pd.DataFrame(rows)


def _load_libertadores(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8")
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "date": parse_date(r.get("datetime")),
            "home_team": str(r.get("home_team")).strip(),
            "away_team": str(r.get("away_team")).strip(),
            "home_team_state": None,
            "away_team_state": None,
            "home_goal": _to_int(r.get("home_goal")),
            "away_goal": _to_int(r.get("away_goal")),
            "season": _to_int(r.get("season")),
            "round": None,
            "stage": r.get("stage"),
            "competition": "Copa Libertadores",
            "source": "Libertadores_Matches.csv",
        })
    return pd.DataFrame(rows)


def _load_br_football(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8")
    rows = []
    for _, r in df.iterrows():
        season = None
        d = parse_date(r.get("date"))
        if d is not None:
            season = d.year
        rows.append({
            "date": d,
            "home_team": str(r.get("home")).strip(),
            "away_team": str(r.get("away")).strip(),
            "home_team_state": None,
            "away_team_state": None,
            "home_goal": _to_int(r.get("home_goal")),
            "away_goal": _to_int(r.get("away_goal")),
            "season": season,
            "round": None,
            "stage": None,
            "competition": str(r.get("tournament")).strip(),
            "source": "BR-Football-Dataset.csv",
            "home_corners": _to_int(r.get("home_corner")),
            "away_corners": _to_int(r.get("away_corner")),
            "home_shots": _to_int(r.get("home_shots")),
            "away_shots": _to_int(r.get("away_shots")),
            "home_attack": _to_int(r.get("home_attack")),
            "away_attack": _to_int(r.get("away_attack")),
            "ht_result": r.get("ht_result"),
            "at_result": r.get("at_result"),
        })
    return pd.DataFrame(rows)


def _load_historical(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8")
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "date": parse_date(r.get("Data")),
            "home_team": str(r.get("Equipe_mandante")).strip(),
            "away_team": str(r.get("Equipe_visitante")).strip(),
            "home_team_state": r.get("Mandante_UF"),
            "away_team_state": r.get("Visitante_UF"),
            "home_goal": _to_int(r.get("Gols_mandante")),
            "away_goal": _to_int(r.get("Gols_visitante")),
            "season": _to_int(r.get("Ano")),
            "round": r.get("Rodada"),
            "stage": None,
            "competition": "Brasileirao Serie A (Historico 2003-2019)",
            "arena": r.get("Arena"),
            "winner": r.get("Vencedor"),
            "source": "novo_campeonato_brasileiro.csv",
        })
    return pd.DataFrame(rows)


def _load_fifa(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8")
    # Keep the most useful columns; the FIFA CSV has 70+ columns.
    keep = [
        "ID", "Name", "Age", "Nationality", "Overall", "Potential", "Club",
        "Position", "Jersey Number", "Height", "Weight", "Value", "Wage",
        "Preferred Foot", "International Reputation",
    ]
    cols = [c for c in keep if c in df.columns]
    df = df[cols].copy()
    df["club_normalized"] = df["Club"].apply(normalize_team_name) if "Club" in df.columns else ""
    df["name_normalized"] = df["Name"].apply(normalize_team_name) if "Name" in df.columns else ""
    df["nationality_normalized"] = df["Nationality"].apply(normalize_team_name) if "Nationality" in df.columns else ""
    return df


def _add_normalized_teams(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        df["home_team_norm"] = []
        df["away_team_norm"] = []
        df["home_team_display"] = []
        df["away_team_display"] = []
        return df
    df["home_team_norm"] = df["home_team"].apply(normalize_team_name)
    df["away_team_norm"] = df["away_team"].apply(normalize_team_name)
    df["home_team_display"] = df["home_team"].apply(display_team_name)
    df["away_team_display"] = df["away_team"].apply(display_team_name)
    return df


class DataLoader:
    """Lazily loads and caches all datasets from the ``data/kaggle`` directory."""

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or default_data_dir()

    def _path(self, name: str) -> str:
        return os.path.join(self.data_dir, name)

    @property
    def matches(self) -> pd.DataFrame:
        if getattr(self, "_matches", None) is None:
            frames = []
            loaders = [
                ("Brasileirao_Matches.csv", _load_brasileirao),
                ("Brazilian_Cup_Matches.csv", _load_copa_brasil),
                ("Libertadores_Matches.csv", _load_libertadores),
                ("BR-Football-Dataset.csv", _load_br_football),
                ("novo_campeonato_brasileiro.csv", _load_historical),
            ]
            for fname, loader in loaders:
                p = self._path(fname)
                if os.path.exists(p):
                    frames.append(loader(p))
            if frames:
                df = pd.concat(frames, ignore_index=True, sort=False)
            else:
                df = pd.DataFrame()
            _add_normalized_teams(df)
            self._matches = df
        return self._matches

    @property
    def players(self) -> pd.DataFrame:
        if getattr(self, "_players", None) is None:
            p = self._path("fifa_data.csv")
            if os.path.exists(p):
                self._players = _load_fifa(p)
            else:
                self._players = pd.DataFrame()
        return self._players

    def competitions(self) -> list[str]:
        if self.matches.empty:
            return []
        return sorted(self.matches["competition"].dropna().unique().tolist())

    def seasons(self, competition: Optional[str] = None) -> list[int]:
        if self.matches.empty:
            return []
        sub = self.matches
        if competition:
            sub = sub[sub["competition"] == competition]
        return sorted([int(s) for s in sub["season"].dropna().unique().tolist()])


@lru_cache(maxsize=1)
def get_loader() -> DataLoader:
    """Return a process-wide cached ``DataLoader`` instance."""
    return DataLoader()
