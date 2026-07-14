"""
Brazilian Soccer MCP Server — Data Loader
==========================================
Loads and normalizes all 6 CSV datasets into unified pandas DataFrames.
Handles team-name variations (state suffixes, full names, accents),
multiple date formats, and type coercion. Exposes a SoccerData class
that lazily loads everything on first access and caches the result.

Data sources
------------
1. Brasileirao_Matches.csv    — Brasileirão Série A (2012–2023)
2. Brazilian_Cup_Matches.csv  — Copa do Brasil (2012–2023)
3. Libertadores_Matches.csv   — Copa Libertadores (2013–2023)
4. BR-Football-Dataset.csv    — Extended match stats (multiple competitions)
5. novo_campeonato_brasileiro.csv — Historical Brasileirão (2003–2019)
6. fifa_data.csv              — FIFA player database (~18k players)
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pandas as pd

_DATA_DIR = Path(__file__).resolve().parent / "data" / "kaggle"

# ── Team-name normalisation ──────────────────────────────────────────

# Strip state suffixes like "-SP", " - RJ", "(antigo …)" and collapse
# whitespace/accent variations so that lookups are consistent.
_SUFFIX_RE = re.compile(r"\s*[-–]\s*[A-Z]{2}\s*$")
_PARENS_RE = re.compile(r"\s*\(antigo[^)]*\)\s*$", re.IGNORECASE)


def normalize_team(name: str) -> str:
    """Return a canonical team name: trimmed, no state suffix, no parenthetical."""
    if not isinstance(name, str):
        return ""
    s = name.strip()
    s = _PARENS_RE.sub("", s)
    s = _SUFFIX_RE.sub("", s)
    return s.strip()


# ── Date helpers ─────────────────────────────────────────────────────

def _parse_date_col(series: pd.Series) -> pd.Series:
    """Parse a date column that may be ISO or DD/MM/YYYY.
    Try ISO (year-first) first; fall back to day-first format."""
    iso = pd.to_datetime(series, format="mixed", errors="coerce")
    return iso.where(
        iso.notna(),
        pd.to_datetime(series, dayfirst=True, format="mixed", errors="coerce"),
    )


# ── Loader ───────────────────────────────────────────────────────────

class SoccerData:
    """Lazy-loaded, cached access to all datasets."""

    def __init__(self, data_dir: str | Path | None = None):
        self._dir = Path(data_dir) if data_dir else _DATA_DIR
        self._brasileirao: pd.DataFrame | None = None
        self._cup: pd.DataFrame | None = None
        self._libertadores: pd.DataFrame | None = None
        self._extended: pd.DataFrame | None = None
        self._historical: pd.DataFrame | None = None
        self._players: pd.DataFrame | None = None

    # ── individual loaders ───────────────────────────────────────────

    def _load_brasileirao(self) -> pd.DataFrame:
        df = pd.read_csv(self._dir / "Brasileirao_Matches.csv")
        df.columns = df.columns.str.strip()
        df["date"] = _parse_date_col(df["datetime"])
        df["home_team"] = df["home_team"].apply(normalize_team)
        df["away_team"] = df["away_team"].apply(normalize_team)
        df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
        df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
        df["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")
        df["competition"] = "Brasileirão"
        return df

    def _load_cup(self) -> pd.DataFrame:
        df = pd.read_csv(self._dir / "Brazilian_Cup_Matches.csv")
        df.columns = df.columns.str.strip()
        df["date"] = _parse_date_col(df["datetime"])
        df["home_team"] = df["home_team"].apply(normalize_team)
        df["away_team"] = df["away_team"].apply(normalize_team)
        df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
        df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
        df["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")
        df["competition"] = "Copa do Brasil"
        return df

    def _load_libertadores(self) -> pd.DataFrame:
        df = pd.read_csv(self._dir / "Libertadores_Matches.csv")
        df.columns = df.columns.str.strip()
        df["date"] = _parse_date_col(df["datetime"])
        df["home_team"] = df["home_team"].apply(normalize_team)
        df["away_team"] = df["away_team"].apply(normalize_team)
        df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
        df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
        df["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")
        df["competition"] = "Copa Libertadores"
        return df

    def _load_extended(self) -> pd.DataFrame:
        df = pd.read_csv(self._dir / "BR-Football-Dataset.csv")
        df.columns = df.columns.str.strip()
        df["date"] = _parse_date_col(df["date"])
        df["home_team"] = df["home"].apply(normalize_team)
        df["away_team"] = df["away"].apply(normalize_team)
        df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
        df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
        df["competition"] = df["tournament"].fillna("Unknown")
        return df

    def _load_historical(self) -> pd.DataFrame:
        df = pd.read_csv(self._dir / "novo_campeonato_brasileiro.csv")
        df.columns = df.columns.str.strip()
        df["date"] = _parse_date_col(df["Data"])
        df["home_team"] = df["Equipe_mandante"].apply(normalize_team)
        df["away_team"] = df["Equipe_visitante"].apply(normalize_team)
        df["home_goal"] = pd.to_numeric(df["Gols_mandante"], errors="coerce")
        df["away_goal"] = pd.to_numeric(df["Gols_visitante"], errors="coerce")
        df["season"] = pd.to_numeric(df["Ano"], errors="coerce").astype("Int64")
        df["round"] = pd.to_numeric(df["Rodada"], errors="coerce").astype("Int64")
        df["competition"] = "Brasileirão (Historical)"
        df["stadium"] = df["Arena"].fillna("")
        return df

    def _load_players(self) -> pd.DataFrame:
        df = pd.read_csv(self._dir / "fifa_data.csv", encoding="utf-8-sig")
        df.columns = df.columns.str.strip()
        # Keep only the columns we actually use to save memory
        keep = [
            "ID", "Name", "Age", "Nationality", "Overall", "Potential",
            "Club", "Position", "Jersey Number", "Height", "Weight",
            "Crossing", "Finishing", "Dribbling", "ShortPassing",
            "LongPassing", "BallControl", "Acceleration", "SprintSpeed",
            "Agility", "Reactions", "Stamina", "Strength", "Vision",
        ]
        available = [c for c in keep if c in df.columns]
        df = df[available].copy()
        df["Overall"] = pd.to_numeric(df["Overall"], errors="coerce")
        df["Potential"] = pd.to_numeric(df["Potential"], errors="coerce")
        df["Age"] = pd.to_numeric(df["Age"], errors="coerce").astype("Int64")
        return df

    # ── public accessors (lazy + cached) ─────────────────────────────

    @property
    def brasileirao(self) -> pd.DataFrame:
        if self._brasileirao is None:
            self._brasileirao = self._load_brasileirao()
        return self._brasileirao

    @property
    def cup(self) -> pd.DataFrame:
        if self._cup is None:
            self._cup = self._load_cup()
        return self._cup

    @property
    def libertadores(self) -> pd.DataFrame:
        if self._libertadores is None:
            self._libertadores = self._load_libertadores()
        return self._libertadores

    @property
    def extended(self) -> pd.DataFrame:
        if self._extended is None:
            self._extended = self._load_extended()
        return self._extended

    @property
    def historical(self) -> pd.DataFrame:
        if self._historical is None:
            self._historical = self._load_historical()
        return self._historical

    @property
    def players(self) -> pd.DataFrame:
        if self._players is None:
            self._players = self._load_players()
        return self._players

    # ── unified match view ───────────────────────────────────────────

    _MATCH_COLS = [
        "date", "home_team", "away_team", "home_goal", "away_goal",
        "season", "competition", "round",
    ]

    def all_matches(self) -> pd.DataFrame:
        """Return a single DataFrame with matches from all sources."""
        frames = []

        def _select(df: pd.DataFrame) -> pd.DataFrame:
            cols = [c for c in self._MATCH_COLS if c in df.columns]
            return df[cols].copy()

        frames.append(_select(self.brasileirao))
        frames.append(_select(self.cup))
        frames.append(_select(self.libertadores))
        frames.append(_select(self.extended))
        frames.append(_select(self.historical))
        return pd.concat(frames, ignore_index=True)

    # ── convenience: team name matching ──────────────────────────────

    def find_team_matches(self, team: str, side: str = "either") -> pd.DataFrame:
        """Find all matches involving *team*.
        side: 'home', 'away', or 'either'.
        """
        all_m = self.all_matches()
        if side == "home":
            return all_m[all_m["home_team"] == normalize_team(team)]
        elif side == "away":
            return all_m[all_m["away_team"] == normalize_team(team)]
        t = normalize_team(team)
        return all_m[(all_m["home_team"] == t) | (all_m["away_team"] == t)]
