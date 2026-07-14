# ============================================================================
# Context: Brazilian Soccer MCP Server benchmark.
# Data loader. Reads the 6 Kaggle CSVs from `data/kaggle/`, normalizes their
# schemas into a single unified Match record and a player DataFrame, and caches
# them in memory. All match files share a common Match dataclass so the query
# engine can treat them uniformly regardless of source competition.
# ----------------------------------------------------------------------------
from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional

import pandas as pd

from .normalizers import (
    canonical_team_name,
    normalize_competition,
    parse_date,
    team_key,
    to_int,
)

DEFAULT_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "kaggle",
)

# Competition labels applied to records from each source file.
COMP_BRASILEIRAO = "Brasileirao"
COMP_COPA_BRASIL = "Copa do Brasil"
COMP_LIBERTADORES = "Copa Libertadores"
COMP_BR_DATASET = "BR-Football-Dataset"  # tournament column varies per row
COMP_HISTORICAL = "Brasileirao (2003-2019)"


@dataclass
class Match:
    """Unified match record produced from every CSV source."""

    competition: str
    season: Optional[int]
    date: Optional[datetime]
    home_team: str           # canonical display name
    away_team: str
    home_team_key: str       # normalized matching key
    away_team_key: str
    home_goals: int
    away_goals: int
    round: Optional[str] = None
    stage: Optional[str] = None
    stadium: Optional[str] = None
    home_state: Optional[str] = None
    away_state: Optional[str] = None
    ht_result: Optional[str] = None
    total_corners: Optional[int] = None
    home_shots: Optional[int] = None
    away_shots: Optional[int] = None
    source_file: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def winner_key(self) -> Optional[str]:
        """Return the team_key of the winner, or None for a draw."""
        if self.home_goals > self.away_goals:
            return self.home_team_key
        if self.away_goals > self.home_goals:
            return self.away_team_key
        return None


class DataLoader:
    """Load and cache all datasets, returning unified match + player objects."""

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or DEFAULT_DATA_DIR
        self._matches: Optional[list[Match]] = None
        self._matches_df: Optional[pd.DataFrame] = None
        self._players_df: Optional[pd.DataFrame] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @property
    def matches(self) -> list[Match]:
        if self._matches is None:
            self._matches = self._load_all_matches()
        return self._matches

    @property
    def matches_df(self) -> pd.DataFrame:
        if self._matches_df is None:
            rows = [m.to_dict() for m in self.matches]
            df = pd.DataFrame(rows)
            # Convert date column to pandas datetime for range filtering.
            if not df.empty:
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
            self._matches_df = df
        return self._matches_df

    @property
    def players_df(self) -> pd.DataFrame:
        if self._players_df is None:
            self._players_df = self._load_players()
        return self._players_df

    def team_index(self) -> dict[str, str]:
        """Return mapping of team_key -> canonical display name (best guess)."""
        idx: dict[str, str] = {}
        for m in self.matches:
            if m.home_team_key:
                idx.setdefault(m.home_team_key, m.home_team)
            if m.away_team_key:
                idx.setdefault(m.away_team_key, m.away_team)
        return idx

    # ------------------------------------------------------------------
    # Internal loaders
    # ------------------------------------------------------------------
    def _load_all_matches(self) -> list[Match]:
        matches: list[Match] = []
        matches += self._load_brasileirao()
        matches += self._load_copa_brasil()
        matches += self._load_libertadores()
        matches += self._load_br_football_dataset()
        matches += self._load_historical_brasileirao()
        # Deduplicate matches that appear in more than one source file
        # (e.g. Brasileirao_Matches and BR-Football-Dataset both cover Serie A
        # 2020-2022). Key on the normalized competition + date + teams + score.
        seen: set[tuple] = set()
        unique: list[Match] = []
        for m in matches:
            key = (
                m.competition,
                m.date.date().isoformat() if m.date else None,
                m.home_team_key,
                m.away_team_key,
                m.home_goals,
                m.away_goals,
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(m)
        return unique

    def _load_brasileirao(self) -> list[Match]:
        path = os.path.join(self.data_dir, "Brasileirao_Matches.csv")
        if not os.path.exists(path):
            return []
        df = pd.read_csv(path)
        out: list[Match] = []
        for _, r in df.iterrows():
            out.append(
                Match(
                    competition=COMP_BRASILEIRAO,
                    season=to_int(r.get("season")),
                    date=parse_date(r.get("datetime")),
                    home_team=canonical_team_name(str(r.get("home_team", ""))),
                    away_team=canonical_team_name(str(r.get("away_team", ""))),
                    home_team_key=team_key(str(r.get("home_team", ""))),
                    away_team_key=team_key(str(r.get("away_team", ""))),
                    home_goals=to_int(r.get("home_goal")),
                    away_goals=to_int(r.get("away_goal")),
                    round=str(r.get("round")) if pd.notna(r.get("round")) else None,
                    home_state=str(r.get("home_team_state")) if pd.notna(r.get("home_team_state")) else None,
                    away_state=str(r.get("away_team_state")) if pd.notna(r.get("away_team_state")) else None,
                    source_file="Brasileirao_Matches.csv",
                )
            )
        return out

    def _load_copa_brasil(self) -> list[Match]:
        path = os.path.join(self.data_dir, "Brazilian_Cup_Matches.csv")
        if not os.path.exists(path):
            return []
        df = pd.read_csv(path)
        out: list[Match] = []
        for _, r in df.iterrows():
            out.append(
                Match(
                    competition=COMP_COPA_BRASIL,
                    season=to_int(r.get("season")),
                    date=parse_date(r.get("datetime")),
                    home_team=canonical_team_name(str(r.get("home_team", ""))),
                    away_team=canonical_team_name(str(r.get("away_team", ""))),
                    home_team_key=team_key(str(r.get("home_team", ""))),
                    away_team_key=team_key(str(r.get("away_team", ""))),
                    home_goals=to_int(r.get("home_goal")),
                    away_goals=to_int(r.get("away_goal")),
                    round=str(r.get("round")) if pd.notna(r.get("round")) else None,
                    source_file="Brazilian_Cup_Matches.csv",
                )
            )
        return out

    def _load_libertadores(self) -> list[Match]:
        path = os.path.join(self.data_dir, "Libertadores_Matches.csv")
        if not os.path.exists(path):
            return []
        df = pd.read_csv(path)
        out: list[Match] = []
        for _, r in df.iterrows():
            out.append(
                Match(
                    competition=COMP_LIBERTADORES,
                    season=to_int(r.get("season")),
                    date=parse_date(r.get("datetime")),
                    home_team=canonical_team_name(str(r.get("home_team", ""))),
                    away_team=canonical_team_name(str(r.get("away_team", ""))),
                    home_team_key=team_key(str(r.get("home_team", ""))),
                    away_team_key=team_key(str(r.get("away_team", ""))),
                    home_goals=to_int(r.get("home_goal")),
                    away_goals=to_int(r.get("away_goal")),
                    stage=str(r.get("stage")) if pd.notna(r.get("stage")) else None,
                    source_file="Libertadores_Matches.csv",
                )
            )
        return out

    def _load_br_football_dataset(self) -> list[Match]:
        path = os.path.join(self.data_dir, "BR-Football-Dataset.csv")
        if not os.path.exists(path):
            return []
        df = pd.read_csv(path)
        out: list[Match] = []
        for _, r in df.iterrows():
            tournament = str(r.get("tournament")) if pd.notna(r.get("tournament")) else "Unknown"
            out.append(
                Match(
                    competition=normalize_competition(tournament),
                    season=_infer_season(r.get("date")),
                    date=parse_date(r.get("date")),
                    home_team=canonical_team_name(str(r.get("home", ""))),
                    away_team=canonical_team_name(str(r.get("away", ""))),
                    home_team_key=team_key(str(r.get("home", ""))),
                    away_team_key=team_key(str(r.get("away", ""))),
                    home_goals=to_int(r.get("home_goal")),
                    away_goals=to_int(r.get("away_goal")),
                    ht_result=str(r.get("ht_result")) if pd.notna(r.get("ht_result")) else None,
                    total_corners=to_int(r.get("total_corners")) if pd.notna(r.get("total_corners")) else None,
                    home_shots=to_int(r.get("home_shots")) if pd.notna(r.get("home_shots")) else None,
                    away_shots=to_int(r.get("away_shots")) if pd.notna(r.get("away_shots")) else None,
                    source_file="BR-Football-Dataset.csv",
                )
            )
        return out

    def _load_historical_brasileirao(self) -> list[Match]:
        path = os.path.join(self.data_dir, "novo_campeonato_brasileiro.csv")
        if not os.path.exists(path):
            return []
        df = pd.read_csv(path)
        out: list[Match] = []
        for _, r in df.iterrows():
            out.append(
                Match(
                    competition=COMP_HISTORICAL,
                    season=to_int(r.get("Ano")),
                    date=parse_date(r.get("Data")),
                    home_team=canonical_team_name(str(r.get("Equipe_mandante", ""))),
                    away_team=canonical_team_name(str(r.get("Equipe_visitante", ""))),
                    home_team_key=team_key(str(r.get("Equipe_mandante", ""))),
                    away_team_key=team_key(str(r.get("Equipe_visitante", ""))),
                    home_goals=to_int(r.get("Gols_mandante")),
                    away_goals=to_int(r.get("Gols_visitante")),
                    round=str(r.get("Rodada")) if pd.notna(r.get("Rodada")) else None,
                    home_state=str(r.get("Mandante_UF")) if pd.notna(r.get("Mandante_UF")) else None,
                    away_state=str(r.get("Visitante_UF")) if pd.notna(r.get("Visitante_UF")) else None,
                    stadium=str(r.get("Arena")) if pd.notna(r.get("Arena")) else None,
                    source_file="novo_campeonato_brasileiro.csv",
                )
            )
        return out

    def _load_players(self) -> pd.DataFrame:
        path = os.path.join(self.data_dir, "fifa_data.csv")
        if not os.path.exists(path):
            return pd.DataFrame()
        df = pd.read_csv(path)
        # Normalize the Club column into a matching key for cross-file joins.
        df["club_key"] = df["Club"].astype(str).map(team_key)
        df["nationality_key"] = df["Nationality"].astype(str).map(team_key)
        return df


def _infer_season(date_value) -> Optional[int]:
    """Infer the season year from a date value (ISO or otherwise)."""
    dt = parse_date(date_value)
    return dt.year if dt else None
