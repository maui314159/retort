"""
================================================================================
Context
--------------------------------------------------------------------------------
Module  : brazilian_soccer.loader
Purpose : Read the six Kaggle CSVs into uniform MatchRecord / PlayerRecord lists
          and build a SoccerGraph. Each source file has different column names
          and conventions; this module is the single place that knows the
          per-file schema, delegating value cleanup to brazilian_soccer.normalize.

Output  :
  MatchRecord  - one per match row, with canonical + display team names,
                 parsed date, integer goals, competition label and season.
  PlayerRecord - one per FIFA player row, with rating/position/club/nationality.

The loader skips rows whose scores cannot be parsed (recorded as None) only for
statistics that require them; the raw record is still kept so listing queries
("which matches did X play") remain complete.
================================================================================
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional

import pandas as pd

from .normalize import display_team, normalize_team, parse_date, parse_score, team_key

# Repository-relative default location of the datasets.
_DEFAULT_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "kaggle"
)

# Canonical competition labels.
BRASILEIRAO = "Brasileirão"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"


@dataclass(slots=True)
class MatchRecord:
    """A single match, normalized across all source files."""

    competition: str
    season: Optional[int]
    match_date: Optional[date]
    home_key: str
    away_key: str
    home_name: str
    away_name: str
    home_goal: Optional[int]
    away_goal: Optional[int]
    round: Optional[str] = None
    stage: Optional[str] = None
    source: str = ""

    @property
    def has_score(self) -> bool:
        return self.home_goal is not None and self.away_goal is not None

    def winner_key(self) -> Optional[str]:
        """Canonical key of the winning team, or None for a draw/unknown."""
        if not self.has_score:
            return None
        if self.home_goal > self.away_goal:
            return self.home_key
        if self.away_goal > self.home_goal:
            return self.away_key
        return None


@dataclass(slots=True)
class PlayerRecord:
    """A single FIFA player."""

    player_id: int
    name: str
    age: Optional[int]
    nationality: str
    overall: Optional[int]
    potential: Optional[int]
    club: str
    club_key: str
    position: str


def _to_int(value: object) -> Optional[int]:
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    return int(f)


def _load_brasileirao(path: str) -> List[MatchRecord]:
    df = pd.read_csv(path)
    out: List[MatchRecord] = []
    for r in df.itertuples(index=False):
        out.append(
            MatchRecord(
                competition=BRASILEIRAO,
                season=_to_int(r.season),
                match_date=parse_date(r.datetime),
                home_key=team_key(r.home_team),
                away_key=team_key(r.away_team),
                home_name=display_team(r.home_team),
                away_name=display_team(r.away_team),
                home_goal=parse_score(r.home_goal),
                away_goal=parse_score(r.away_goal),
                round=None if pd.isna(r.round) else str(_to_int(r.round) or r.round),
                source="Brasileirao_Matches.csv",
            )
        )
    return out


def _load_cup(path: str) -> List[MatchRecord]:
    df = pd.read_csv(path)
    out: List[MatchRecord] = []
    for r in df.itertuples(index=False):
        out.append(
            MatchRecord(
                competition=COPA_DO_BRASIL,
                season=_to_int(r.season),
                match_date=parse_date(r.datetime),
                home_key=team_key(r.home_team),
                away_key=team_key(r.away_team),
                home_name=display_team(r.home_team),
                away_name=display_team(r.away_team),
                home_goal=parse_score(r.home_goal),
                away_goal=parse_score(r.away_goal),
                round=None if pd.isna(r.round) else str(r.round),
                source="Brazilian_Cup_Matches.csv",
            )
        )
    return out


def _load_libertadores(path: str) -> List[MatchRecord]:
    df = pd.read_csv(path)
    out: List[MatchRecord] = []
    for r in df.itertuples(index=False):
        out.append(
            MatchRecord(
                competition=LIBERTADORES,
                season=_to_int(r.season),
                match_date=parse_date(r.datetime),
                home_key=team_key(r.home_team),
                away_key=team_key(r.away_team),
                home_name=display_team(r.home_team),
                away_name=display_team(r.away_team),
                home_goal=parse_score(r.home_goal),
                away_goal=parse_score(r.away_goal),
                stage=None if pd.isna(r.stage) else str(r.stage),
                source="Libertadores_Matches.csv",
            )
        )
    return out


def _load_extended(path: str) -> List[MatchRecord]:
    df = pd.read_csv(path)
    out: List[MatchRecord] = []
    for r in df.itertuples(index=False):
        d = parse_date(r.date)
        out.append(
            MatchRecord(
                competition=str(r.tournament),
                season=d.year if d else None,
                match_date=d,
                home_key=team_key(r.home),
                away_key=team_key(r.away),
                home_name=display_team(r.home),
                away_name=display_team(r.away),
                home_goal=parse_score(r.home_goal),
                away_goal=parse_score(r.away_goal),
                source="BR-Football-Dataset.csv",
            )
        )
    return out


def _load_historical(path: str) -> List[MatchRecord]:
    df = pd.read_csv(path)
    out: List[MatchRecord] = []
    for r in df.itertuples(index=False):
        out.append(
            MatchRecord(
                competition=BRASILEIRAO,
                season=_to_int(r.Ano),
                match_date=parse_date(r.Data),
                home_key=team_key(r.Equipe_mandante),
                away_key=team_key(r.Equipe_visitante),
                home_name=display_team(r.Equipe_mandante),
                away_name=display_team(r.Equipe_visitante),
                home_goal=parse_score(r.Gols_mandante),
                away_goal=parse_score(r.Gols_visitante),
                round=None if pd.isna(r.Rodada) else str(_to_int(r.Rodada)),
                source="novo_campeonato_brasileiro.csv",
            )
        )
    return out


def _load_players(path: str) -> List[PlayerRecord]:
    df = pd.read_csv(path)
    out: List[PlayerRecord] = []
    for r in df.itertuples(index=False):
        club = "" if pd.isna(r.Club) else str(r.Club).strip()
        out.append(
            PlayerRecord(
                player_id=_to_int(r.ID) or -1,
                name="" if pd.isna(r.Name) else str(r.Name).strip(),
                age=_to_int(r.Age),
                nationality="" if pd.isna(r.Nationality) else str(r.Nationality).strip(),
                overall=_to_int(r.Overall),
                potential=_to_int(r.Potential),
                club=club,
                club_key=normalize_team(club),
                position="" if pd.isna(r.Position) else str(r.Position).strip(),
            )
        )
    return out


# Filename -> loader for the dedicated (authoritative) match files. These are
# loaded first and own every (competition, season) they contain.
_DEDICATED_LOADERS = {
    "Brasileirao_Matches.csv": _load_brasileirao,
    "Brazilian_Cup_Matches.csv": _load_cup,
    "Libertadores_Matches.csv": _load_libertadores,
    "novo_campeonato_brasileiro.csv": _load_historical,
}

# BR-Football tournament label -> canonical competition. Serie A IS the
# Brasileirão; Copa do Brasil overlaps the dedicated cup file. Both are admitted
# only for seasons the dedicated files do not already cover (e.g. 2023). Labels
# absent here (Serie B, Serie C) are unique to this file and always kept.
_EXTENDED_CANONICAL = {
    "Serie A": BRASILEIRAO,
    "Copa do Brasil": COPA_DO_BRASIL,
}


def load_matches(data_dir: str = _DEFAULT_DATA_DIR) -> List[MatchRecord]:
    """Load every match dataset under *data_dir* without cross-source overlap.

    Several files cover the same competition+season with differing completeness:
    the dedicated Brasileirão file has scoreless (postponed/missing) rows for
    2016 and 2022, while BR-Football-Dataset.csv ("Serie A") carries complete
    scores for 2014-2023 and is the only source for 2023. Rather than merge rows
    across sources with mismatched team-name conventions, we pick, per
    (canonical competition, season), the single source with the most *scored*
    matches and keep only its rows. This guarantees no double-counting and the
    most complete table for every season. Serie B / Serie C exist only in
    BR-Football, so they win their seasons unopposed.
    """
    # source label -> its (relabeled) records.
    per_source: List[tuple] = []
    for filename, fn in _DEDICATED_LOADERS.items():
        path = os.path.join(data_dir, filename)
        if os.path.exists(path):
            per_source.append((filename, fn(path)))

    ext_path = os.path.join(data_dir, "BR-Football-Dataset.csv")
    if os.path.exists(ext_path):
        ext: List[MatchRecord] = []
        for m in _load_extended(ext_path):
            m.competition = _EXTENDED_CANONICAL.get(m.competition, m.competition)
            ext.append(m)
        per_source.append(("BR-Football-Dataset.csv", ext))

    # Score how completely each source covers each (competition, season).
    scored: Dict[tuple, Dict[str, int]] = {}
    for label, records in per_source:
        for m in records:
            if m.season is None:
                continue
            slot = scored.setdefault((m.competition, m.season), {})
            slot[label] = slot.get(label, 0) + (1 if m.has_score else 0)

    # Winning source per (competition, season): most scored matches, ties broken
    # by dedicated-file load order (first wins).
    order = {label: i for i, (label, _) in enumerate(per_source)}
    winner: Dict[tuple, str] = {}
    for pair, counts in scored.items():
        winner[pair] = min(counts, key=lambda lbl: (-counts[lbl], order[lbl]))

    matches: List[MatchRecord] = []
    for label, records in per_source:
        for m in records:
            if m.season is None or winner.get((m.competition, m.season)) == label:
                matches.append(m)
    return matches


def load_players(data_dir: str = _DEFAULT_DATA_DIR) -> List[PlayerRecord]:
    """Load the FIFA player dataset from *data_dir* (empty list if absent)."""
    path = os.path.join(data_dir, "fifa_data.csv")
    return _load_players(path) if os.path.exists(path) else []


def load_graph(data_dir: str = _DEFAULT_DATA_DIR) -> "SoccerGraph":
    """Build a fully-indexed SoccerGraph from the datasets under *data_dir*."""
    from .graph import SoccerGraph

    return SoccerGraph(load_matches(data_dir), load_players(data_dir))
