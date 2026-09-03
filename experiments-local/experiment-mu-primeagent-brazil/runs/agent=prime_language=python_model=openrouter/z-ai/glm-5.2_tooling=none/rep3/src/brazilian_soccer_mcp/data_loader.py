"""
Context Block
=============

Module: brazilian_soccer_mcp.data_loader
Purpose: Load the six Kaggle CSV datasets and unify them into a
         single list of normalised ``MatchRecord`` objects and a
         list of ``PlayerRecord`` objects.

Datasets handled
----------------
1. Brasileirao_Matches.csv        - Serie A matches 2012-2022
2. Brazilian_Cup_Matches.csv      - Copa do Brasil 2012-2023
3. Libertadores_Matches.csv       - Copa Libertadores 2013-2023
4. BR-Football-Dataset.csv        - Extended stats (2023, all divisions)
5. novo_campeonato_brasileiro.csv - Historical Brasileirao 2003-2019
6. fifa_data.csv                  - FIFA player database (~18k players)

Each CSV is read with pandas, normalised via the helpers in
``normalizer.py``, and converted to the dataclasses defined below.
The ``DataLoader`` class provides a single ``load()`` entry point
that returns ``self`` with ``self.matches`` and ``self.players``
populated.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

import pandas as pd

from .normalizer import (
    team_match_key,
    team_state,
    display_name,
    parse_date,
    format_date,
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class MatchRecord:
    """A single match in a unified, source-agnostic format."""

    match_id: str
    date: Optional[datetime]
    home_team: str            # display name (no state suffix)
    away_team: str            # display name (no state suffix)
    home_team_key: str        # normalised match key
    away_team_key: str        # normalised match key
    home_state: Optional[str]
    away_state: Optional[str]
    home_goals: Optional[int]
    away_goals: Optional[int]
    competition: str          # canonical competition name
    season: Optional[int]
    round_info: Optional[str]
    stage: Optional[str]      # Libertadores stage or similar
    source_file: str
    # Extended stats (BR-Football only; None for other sources)
    home_corners: Optional[float] = None
    away_corners: Optional[float] = None
    home_shots: Optional[float] = None
    away_shots: Optional[float] = None
    home_attacks: Optional[float] = None
    away_attacks: Optional[float] = None
    total_corners: Optional[float] = None
    ht_result: Optional[str] = None
    at_result: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["date"] = format_date(self.date)
        return d


@dataclass
class PlayerRecord:
    """A single player from the FIFA dataset."""

    player_id: int
    name: str
    age: Optional[int]
    nationality: str
    overall: Optional[int]
    potential: Optional[int]
    club: str
    club_key: str            # normalised club key for matching
    position: Optional[str]
    jersey_number: Optional[int]
    height: Optional[str]
    weight: Optional[str]
    preferred_foot: Optional[str]
    value: Optional[str]
    wage: Optional[str]
    crossing: Optional[int] = None
    finishing: Optional[int] = None
    dribbling: Optional[int] = None
    short_passing: Optional[int] = None
    long_shots: Optional[int] = None

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Default data directory (relative to this file -> project root / data / kaggle)
# ---------------------------------------------------------------------------
DEFAULT_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "kaggle",
)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------
class DataLoader:
    """Load and unify all CSV datasets.

    Parameters
    ----------
    data_dir : str
        Directory containing the six CSV files.  Defaults to the
        project's ``data/kaggle`` directory.
    """

    COMPETITION_BRASILEIRAO = "Brasileirao"
    COMPETITION_CUP = "Copa do Brasil"
    COMPETITION_LIBERTADORES = "Copa Libertadores"
    COMPETITION_SERIE_A = "Serie A"
    COMPETITION_SERIE_B = "Serie B"
    COMPETITION_SERIE_C = "Serie C"

    def __init__(self, data_dir: str = DEFAULT_DATA_DIR):
        self.data_dir = data_dir
        self.matches: list[MatchRecord] = []
        self.players: list[PlayerRecord] = []
        self._loaded = False

    # -- public API ---------------------------------------------------------
    def load(self) -> "DataLoader":
        """Load all datasets and return ``self``.

        After loading all sources, duplicate matches (same date,
        teams and score) are removed.  The Brasileirao_Matches.csv
        source is loaded first, so for overlapping years (2012-2019)
        its records are kept over the Historical dataset's.
        """
        self.matches = []
        self.players = []
        self._load_brasileirao()
        self._load_cup()
        self._load_libertadores()
        self._load_br_football()
        self._load_historical()
        self._load_fifa()
        self._deduplicate_matches()
        self._loaded = True
        return self

    def _deduplicate_matches(self) -> None:
        """Remove duplicate matches sharing the same date, teams and score.

        The key is ``(date, home_team_key, away_team_key, home_goals,
        away_goals)``.  The first occurrence is kept, which (because
        of load order) prefers Brasileirao_Matches.csv over the
        Historical dataset for overlapping seasons, and
        Brazilian_Cup_Matches.csv over BR-Football for the 2023 cup.
        """
        seen: set[tuple] = set()
        unique: list[MatchRecord] = []
        for m in self.matches:
            date_key = m.date.date() if m.date else None
            key = (date_key, m.home_team_key, m.away_team_key,
                   m.home_goals, m.away_goals)
            if key in seen:
                continue
            seen.add(key)
            unique.append(m)
        self.matches = unique

    # -- helpers ------------------------------------------------------------
    def _path(self, filename: str) -> str:
        return os.path.join(self.data_dir, filename)

    @staticmethod
    def _safe_int(value) -> Optional[int]:
        if value is None:
            return None
        try:
            if pd.isna(value):
                return None
        except (TypeError, ValueError):
            pass
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_float(value) -> Optional[float]:
        if value is None:
            return None
        try:
            if pd.isna(value):
                return None
        except (TypeError, ValueError):
            pass
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_str(value) -> Optional[str]:
        if value is None:
            return None
        try:
            if pd.isna(value):
                return None
        except (TypeError, ValueError):
            pass
        s = str(value).strip()
        return s if s else None

    # -- individual loaders -------------------------------------------------
    def _load_brasileirao(self) -> None:
        path = self._path("Brasileirao_Matches.csv")
        if not os.path.exists(path):
            return
        df = pd.read_csv(path)
        for i, row in df.iterrows():
            ht = str(row.get("home_team", ""))
            at = str(row.get("away_team", ""))
            self.matches.append(MatchRecord(
                match_id=f"bras_{row.get('season', '')}_{i}",
                date=parse_date(row.get("datetime")),
                home_team=display_name(ht),
                away_team=display_name(at),
                home_team_key=team_match_key(ht),
                away_team_key=team_match_key(at),
                home_state=self._safe_str(row.get("home_team_state")),
                away_state=self._safe_str(row.get("away_team_state")),
                home_goals=self._safe_int(row.get("home_goal")),
                away_goals=self._safe_int(row.get("away_goal")),
                competition=self.COMPETITION_BRASILEIRAO,
                season=self._safe_int(row.get("season")),
                round_info=self._safe_str(row.get("round")),
                stage=None,
                source_file="Brasileirao_Matches.csv",
            ))

    def _load_cup(self) -> None:
        path = self._path("Brazilian_Cup_Matches.csv")
        if not os.path.exists(path):
            return
        df = pd.read_csv(path)
        for i, row in df.iterrows():
            ht = str(row.get("home_team", ""))
            at = str(row.get("away_team", ""))
            self.matches.append(MatchRecord(
                match_id=f"cup_{row.get('season', '')}_{i}",
                date=parse_date(row.get("datetime")),
                home_team=display_name(ht),
                away_team=display_name(at),
                home_team_key=team_match_key(ht),
                away_team_key=team_match_key(at),
                home_state=team_state(ht),
                away_state=team_state(at),
                home_goals=self._safe_int(row.get("home_goal")),
                away_goals=self._safe_int(row.get("away_goal")),
                competition=self.COMPETITION_CUP,
                season=self._safe_int(row.get("season")),
                round_info=self._safe_str(row.get("round")),
                stage=None,
                source_file="Brazilian_Cup_Matches.csv",
            ))

    def _load_libertadores(self) -> None:
        path = self._path("Libertadores_Matches.csv")
        if not os.path.exists(path):
            return
        df = pd.read_csv(path)
        for i, row in df.iterrows():
            ht = str(row.get("home_team", ""))
            at = str(row.get("away_team", ""))
            self.matches.append(MatchRecord(
                match_id=f"lib_{row.get('season', '')}_{i}",
                date=parse_date(row.get("datetime")),
                home_team=display_name(ht),
                away_team=display_name(at),
                home_team_key=team_match_key(ht),
                away_team_key=team_match_key(at),
                home_state=team_state(ht),
                away_state=team_state(at),
                home_goals=self._safe_int(row.get("home_goal")),
                away_goals=self._safe_int(row.get("away_goal")),
                competition=self.COMPETITION_LIBERTADORES,
                season=self._safe_int(row.get("season")),
                round_info=None,
                stage=self._safe_str(row.get("stage")),
                source_file="Libertadores_Matches.csv",
            ))

    def _load_br_football(self) -> None:
        path = self._path("BR-Football-Dataset.csv")
        if not os.path.exists(path):
            return
        df = pd.read_csv(path)
        tourney_map = {
            "Serie A": self.COMPETITION_SERIE_A,
            "Serie B": self.COMPETITION_SERIE_B,
            "Serie C": self.COMPETITION_SERIE_C,
            "Copa do Brasil": self.COMPETITION_CUP,
        }
        for i, row in df.iterrows():
            ht = str(row.get("home", ""))
            at = str(row.get("away", ""))
            tourney = str(row.get("tournament", ""))
            competition = tourney_map.get(tourney, tourney)
            dt = parse_date(row.get("date"))
            season = dt.year if dt else None
            self.matches.append(MatchRecord(
                match_id=f"brf_{i}",
                date=dt,
                home_team=display_name(ht),
                away_team=display_name(at),
                home_team_key=team_match_key(ht),
                away_team_key=team_match_key(at),
                home_state=team_state(ht),
                away_state=team_state(at),
                home_goals=self._safe_int(row.get("home_goal")),
                away_goals=self._safe_int(row.get("away_goal")),
                competition=competition,
                season=season,
                round_info=None,
                stage=None,
                source_file="BR-Football-Dataset.csv",
                home_corners=self._safe_float(row.get("home_corner")),
                away_corners=self._safe_float(row.get("away_corner")),
                home_shots=self._safe_float(row.get("home_shots")),
                away_shots=self._safe_float(row.get("away_shots")),
                home_attacks=self._safe_float(row.get("home_attack")),
                away_attacks=self._safe_float(row.get("away_attack")),
                total_corners=self._safe_float(row.get("total_corners")),
                ht_result=self._safe_str(row.get("ht_result")),
                at_result=self._safe_str(row.get("at_result")),
            ))

    def _load_historical(self) -> None:
        path = self._path("novo_campeonato_brasileiro.csv")
        if not os.path.exists(path):
            return
        df = pd.read_csv(path)
        for i, row in df.iterrows():
            ht = str(row.get("Equipe_mandante", ""))
            at = str(row.get("Equipe_visitante", ""))
            self.matches.append(MatchRecord(
                match_id=f"hist_{row.get('ID', i)}",
                date=parse_date(row.get("Data")),
                home_team=display_name(ht),
                away_team=display_name(at),
                home_team_key=team_match_key(ht),
                away_team_key=team_match_key(at),
                home_state=self._safe_str(row.get("Mandante_UF")),
                away_state=self._safe_str(row.get("Visitante_UF")),
                home_goals=self._safe_int(row.get("Gols_mandante")),
                away_goals=self._safe_int(row.get("Gols_visitante")),
                competition=self.COMPETITION_BRASILEIRAO,
                season=self._safe_int(row.get("Ano")),
                round_info=self._safe_str(row.get("Rodada")),
                stage=None,
                source_file="novo_campeonato_brasileiro.csv",
            ))

    def _load_fifa(self) -> None:
        path = self._path("fifa_data.csv")
        if not os.path.exists(path):
            return
        df = pd.read_csv(path)
        for _, row in df.iterrows():
            club = self._safe_str(row.get("Club")) or ""
            self.players.append(PlayerRecord(
                player_id=self._safe_int(row.get("ID")) or 0,
                name=self._safe_str(row.get("Name")) or "",
                age=self._safe_int(row.get("Age")),
                nationality=self._safe_str(row.get("Nationality")) or "",
                overall=self._safe_int(row.get("Overall")),
                potential=self._safe_int(row.get("Potential")),
                club=club,
                club_key=team_match_key(club) if club else "",
                position=self._safe_str(row.get("Position")),
                jersey_number=self._safe_int(row.get("Jersey Number")),
                height=self._safe_str(row.get("Height")),
                weight=self._safe_str(row.get("Weight")),
                preferred_foot=self._safe_str(row.get("Preferred Foot")),
                value=self._safe_str(row.get("Value")),
                wage=self._safe_str(row.get("Wage")),
                crossing=self._safe_int(row.get("Crossing")),
                finishing=self._safe_int(row.get("Finishing")),
                dribbling=self._safe_int(row.get("Dribbling")),
                short_passing=self._safe_int(row.get("ShortPassing")),
                long_shots=self._safe_int(row.get("LongShots")),
            ))
