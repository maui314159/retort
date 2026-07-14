"""
================================================================================
brazil_soccer_mcp.loaders
================================================================================
Context:
    Reads the six provided CSV datasets and converts each row into a normalized
    Match or Player record. All team names, dates and competition labels pass
    through brazil_soccer_mcp.normalize so downstream code never touches raw,
    inconsistent strings.

Datasets (data/kaggle/):
    Brasileirao_Matches.csv        Brasileirao Serie A 2012-2022 (state suffix)
    Brazilian_Cup_Matches.csv      Copa do Brasil 2012-2021
    Libertadores_Matches.csv       Copa Libertadores 2013-2022 (+ stage)
    BR-Football-Dataset.csv        Serie A/B/C + Copa do Brasil 2014-2023 (stats)
    novo_campeonato_brasileiro.csv Brasileirao Serie A 2003-2019 (BR dates)
    fifa_data.csv                  FIFA player DB (18k players)

Deduplication:
    The match sources overlap (e.g. 2019 Serie A appears in three files). Each
    Match carries `dedup_key = (competition, season, home_key, away_key)`. In a
    single-season round-robin each ordered (home, away) pair occurs once, so
    this key collapses one real fixture reported by multiple sources. The graph
    layer uses it to avoid double counting in standings/aggregates.

Encoding:
    All files are read as UTF-8 to preserve Portuguese accents/cedillas.
================================================================================
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, List, Optional, Tuple

import pandas as pd

from .normalize import (
    display_team,
    normalize_competition,
    normalize_date,
    normalize_team,
    parse_team,
)

DATA_DIR = os.environ.get(
    "BRAZIL_SOCCER_DATA_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "kaggle"),
)


@dataclass
class Match:
    """One normalized match record.

    home_key/away_key hold the accent-folded base name; home_state/away_state
    hold the parsed state/country code (or None). home_ckey/away_ckey are the
    corpus-aware canonical keys assigned by the graph layer once it knows which
    base names are ambiguous (shared across states). winner_key uses ckeys.
    """

    competition: str
    season: Optional[int]
    date: Optional[date]
    home: str
    away: str
    home_key: str
    away_key: str
    home_state: Optional[str]
    away_state: Optional[str]
    home_goal: Optional[int]
    away_goal: Optional[int]
    source: str
    round: Optional[str] = None
    stage: Optional[str] = None
    stats: dict = field(default_factory=dict)
    home_ckey: str = ""
    away_ckey: str = ""

    @property
    def dedup_key(self) -> Tuple[str, Optional[int], str, str]:
        return (self.competition, self.season, self.home_ckey, self.away_ckey)

    @property
    def winner_key(self) -> Optional[str]:
        """home_ckey, away_ckey, or None (draw / unknown score)."""
        if self.home_goal is None or self.away_goal is None:
            return None
        if self.home_goal > self.away_goal:
            return self.home_ckey
        if self.away_goal > self.home_goal:
            return self.away_ckey
        return None  # draw


@dataclass(frozen=True)
class Player:
    """One normalized FIFA player record."""

    id: Optional[int]
    name: str
    name_key: str
    age: Optional[int]
    nationality: str
    nationality_key: str
    overall: Optional[int]
    potential: Optional[int]
    club: str
    club_key: str
    position: str
    jersey: Optional[str]
    height: str
    weight: str


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _to_int(value) -> Optional[int]:
    if value is None:
        return None
    try:
        if isinstance(value, str) and not value.strip():
            return None
        if pd.isna(value):
            return None
        return int(float(value))
    except (ValueError, TypeError):
        return None


def _to_str(value) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (ValueError, TypeError):
        pass
    return str(value).strip()


def _season_from(value, fallback: Optional[date]) -> Optional[int]:
    season = _to_int(value)
    if season is not None:
        return season
    if fallback is not None:
        return fallback.year
    return None


def _make_match(
    competition: str,
    season,
    raw_date,
    home_raw,
    away_raw,
    home_goal,
    away_goal,
    source: str,
    round_=None,
    stage=None,
    stats=None,
) -> Match:
    d = normalize_date(raw_date)
    home = display_team(home_raw)
    away = display_team(away_raw)
    home_base, home_state = parse_team(home_raw)
    away_base, away_state = parse_team(away_raw)
    return Match(
        competition=competition,
        season=_season_from(season, d),
        date=d,
        home=home,
        away=away,
        home_key=home_base,
        away_key=away_base,
        home_state=home_state,
        away_state=away_state,
        home_goal=_to_int(home_goal),
        away_goal=_to_int(away_goal),
        source=source,
        round=_to_str(round_) or None,
        stage=_to_str(stage) or None,
        stats=stats or {},
    )


# --------------------------------------------------------------------------- #
# Per-file loaders
# --------------------------------------------------------------------------- #
def load_brasileirao(path: str) -> List[Match]:
    df = pd.read_csv(path, encoding="utf-8", dtype=str, keep_default_na=False)
    src = os.path.basename(path)
    return [
        _make_match(
            "Brasileirao Serie A",
            r["season"],
            r["datetime"],
            r["home_team"],
            r["away_team"],
            r["home_goal"],
            r["away_goal"],
            src,
            round_=r.get("round"),
        )
        for _, r in df.iterrows()
    ]


def load_cup(path: str) -> List[Match]:
    df = pd.read_csv(path, encoding="utf-8", dtype=str, keep_default_na=False)
    src = os.path.basename(path)
    return [
        _make_match(
            "Copa do Brasil",
            r["season"],
            r["datetime"],
            r["home_team"],
            r["away_team"],
            r["home_goal"],
            r["away_goal"],
            src,
            round_=r.get("round"),
        )
        for _, r in df.iterrows()
    ]


def load_libertadores(path: str) -> List[Match]:
    df = pd.read_csv(path, encoding="utf-8", dtype=str, keep_default_na=False)
    src = os.path.basename(path)
    return [
        _make_match(
            "Copa Libertadores",
            r["season"],
            r["datetime"],
            r["home_team"],
            r["away_team"],
            r["home_goal"],
            r["away_goal"],
            src,
            stage=r.get("stage"),
        )
        for _, r in df.iterrows()
    ]


def load_br_football(path: str) -> List[Match]:
    df = pd.read_csv(path, encoding="utf-8", dtype=str, keep_default_na=False)
    src = os.path.basename(path)
    matches: List[Match] = []
    for _, r in df.iterrows():
        stats = {
            "home_corner": _to_int(r.get("home_corner")),
            "away_corner": _to_int(r.get("away_corner")),
            "home_shots": _to_int(r.get("home_shots")),
            "away_shots": _to_int(r.get("away_shots")),
            "home_attack": _to_int(r.get("home_attack")),
            "away_attack": _to_int(r.get("away_attack")),
            "total_corners": _to_int(r.get("total_corners")),
            "ht_result": _to_str(r.get("ht_result")) or None,
            "at_result": _to_str(r.get("at_result")) or None,
        }
        matches.append(
            _make_match(
                normalize_competition(r["tournament"]),
                None,
                r["date"],
                r["home"],
                r["away"],
                r["home_goal"],
                r["away_goal"],
                src,
                stats=stats,
            )
        )
    return matches


def load_novo(path: str) -> List[Match]:
    df = pd.read_csv(path, encoding="utf-8", dtype=str, keep_default_na=False)
    src = os.path.basename(path)
    matches: List[Match] = []
    for _, r in df.iterrows():
        matches.append(
            _make_match(
                "Brasileirao Serie A",
                r["Ano"],
                r["Data"],
                r["Equipe_mandante"],
                r["Equipe_visitante"],
                r["Gols_mandante"],
                r["Gols_visitante"],
                src,
                round_=r.get("Rodada"),
                stats={"arena": _to_str(r.get("Arena")) or None},
            )
        )
    return matches


def load_players(path: str) -> List[Player]:
    df = pd.read_csv(path, encoding="utf-8", dtype=str, keep_default_na=False)
    players: List[Player] = []
    for _, r in df.iterrows():
        name = _to_str(r.get("Name"))
        nationality = _to_str(r.get("Nationality"))
        club = _to_str(r.get("Club"))
        players.append(
            Player(
                id=_to_int(r.get("ID")),
                name=name,
                name_key=normalize_team(name),
                age=_to_int(r.get("Age")),
                nationality=nationality,
                nationality_key=normalize_team(nationality),
                overall=_to_int(r.get("Overall")),
                potential=_to_int(r.get("Potential")),
                club=club,
                club_key=normalize_team(club),
                position=_to_str(r.get("Position")),
                jersey=_to_str(r.get("Jersey Number")) or None,
                height=_to_str(r.get("Height")),
                weight=_to_str(r.get("Weight")),
            )
        )
    return players


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
_MATCH_FILES = (
    ("Brasileirao_Matches.csv", load_brasileirao),
    ("Brazilian_Cup_Matches.csv", load_cup),
    ("Libertadores_Matches.csv", load_libertadores),
    ("BR-Football-Dataset.csv", load_br_football),
    ("novo_campeonato_brasileiro.csv", load_novo),
)


def load_all_matches(data_dir: str = DATA_DIR) -> List[Match]:
    matches: List[Match] = []
    for filename, loader in _MATCH_FILES:
        path = os.path.join(data_dir, filename)
        if os.path.exists(path):
            matches.extend(loader(path))
    return matches


def load_all_players(data_dir: str = DATA_DIR) -> List[Player]:
    path = os.path.join(data_dir, "fifa_data.csv")
    if os.path.exists(path):
        return load_players(path)
    return []
