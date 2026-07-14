"""Data loading for the Brazilian Soccer MCP server.

Context: This module loads the six Kaggle CSV files listed in TASK.md into a
single in-memory model of matches and players, applying the normalization
rules from :mod:`normalize`. Loading is performed once and cached on a
``DataStore`` instance; the MCP server and the test suite share the same
instance so repeated queries are fast (simple lookups must stay < 2s and
aggregate queries < 5s per the success criteria).

The unified :class:`Match` record intentionally keeps a *display* team name
alongside the normalized key so answers can show "Flamengo" while matching
against "flamengo". Extra statistics from the rich ``BR-Football-Dataset``
(corners, shots, attacks, half-time result) and the historical file (arena,
winner column) are preserved in ``Match.stats``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

import pandas as pd

import normalize as norm

DATA_DIR = os.environ.get(
    "BR_SOCCER_DATA_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "kaggle"),
)


@dataclass(frozen=True)
class Match:
    """A single match, normalized across all source files."""

    competition: str            # canonical competition label
    date: Optional["object"]    # datetime.date or None when unparseable
    season: Optional[int]
    home_team: str              # display name (state suffix preserved)
    away_team: str
    home_state: Optional[str]
    away_state: Optional[str]
    home_goal: Optional[int]
    away_goal: Optional[int]
    stage: str                  # round / stage / arena-free descriptor
    source_file: str
    home_key: str = ""          # normalized base key for fast matching
    away_key: str = ""
    stats: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Player:
    """A FIFA player row, trimmed to the fields the query layer needs."""

    id: int
    name: str
    age: Optional[int]
    nationality: str
    overall: Optional[int]
    potential: Optional[int]
    club: str
    position: str
    jersey: Optional[int]
    height: str
    weight: str
    value: str
    wage: str
    preferred_foot: str
    attributes: dict = field(default_factory=dict)


def _safe_str(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


class DataStore:
    """Holds all loaded matches and players plus convenience indexes."""

    def __init__(self, data_dir: str = DATA_DIR) -> None:
        self.data_dir = data_dir
        self.matches: list[Match] = []
        self.players: list[Player] = []
        self._load_matches()
        self._load_players()

    # -- loading -----------------------------------------------------------
    def _load_matches(self) -> None:
        self.matches.extend(self._load_brasileirao())
        self.matches.extend(self._load_copa_brasil())
        self.matches.extend(self._load_libertadores())
        self.matches.extend(self._load_br_football())
        self.matches.extend(self._load_historical())

    def _load_brasileirao(self) -> list[Match]:
        path = os.path.join(self.data_dir, "Brasileirao_Matches.csv")
        df = pd.read_csv(path)
        out: list[Match] = []
        for row in df.itertuples(index=False):
            home = _safe_str(getattr(row, "home_team"))
            away = _safe_str(getattr(row, "away_team"))
            hbase, hstate = norm.normalize_team(home)
            abase, astate = norm.normalize_team(away)
            out.append(Match(
                competition="Brasileirão Serie A",
                date=norm.parse_date(getattr(row, "datetime", None)),
                season=norm.to_int(getattr(row, "season", None)),
                home_team=home, away_team=away,
                home_state=hstate or _safe_str(getattr(row, "home_team_state", "")) or None,
                away_state=astate or _safe_str(getattr(row, "away_team_state", "")) or None,
                home_goal=norm.to_int(getattr(row, "home_goal", None)),
                away_goal=norm.to_int(getattr(row, "away_goal", None)),
                stage=f"Round {getattr(row, 'round', '')}",
                source_file="Brasileirao_Matches.csv",
                home_key=hbase, away_key=abase,
            ))
        return out

    def _load_copa_brasil(self) -> list[Match]:
        path = os.path.join(self.data_dir, "Brazilian_Cup_Matches.csv")
        df = pd.read_csv(path)
        out: list[Match] = []
        for row in df.itertuples(index=False):
            home = _safe_str(getattr(row, "home_team"))
            away = _safe_str(getattr(row, "away_team"))
            hbase, hstate = norm.normalize_team(home)
            abase, astate = norm.normalize_team(away)
            rnd = getattr(row, "round", "")
            out.append(Match(
                competition="Copa do Brasil",
                date=norm.parse_date(getattr(row, "datetime", None)),
                season=norm.to_int(getattr(row, "season", None)),
                home_team=home, away_team=away,
                home_state=hstate, away_state=astate,
                home_goal=norm.to_int(getattr(row, "home_goal", None)),
                away_goal=norm.to_int(getattr(row, "away_goal", None)),
                stage=_cup_round_label(rnd),
                source_file="Brazilian_Cup_Matches.csv",
                home_key=hbase, away_key=abase,
            ))
        return out

    def _load_libertadores(self) -> list[Match]:
        path = os.path.join(self.data_dir, "Libertadores_Matches.csv")
        df = pd.read_csv(path)
        out: list[Match] = []
        for row in df.itertuples(index=False):
            home = _safe_str(getattr(row, "home_team"))
            away = _safe_str(getattr(row, "away_team"))
            hbase, hstate = norm.normalize_team(home)
            abase, astate = norm.normalize_team(away)
            out.append(Match(
                competition="Copa Libertadores",
                date=norm.parse_date(getattr(row, "datetime", None)),
                season=norm.to_int(getattr(row, "season", None)),
                home_team=home, away_team=away,
                home_state=hstate, away_state=astate,
                home_goal=norm.to_int(getattr(row, "home_goal", None)),
                away_goal=norm.to_int(getattr(row, "away_goal", None)),
                stage=_safe_str(getattr(row, "stage", "stage")),
                source_file="Libertadores_Matches.csv",
                home_key=hbase, away_key=abase,
            ))
        return out

    def _load_br_football(self) -> list[Match]:
        path = os.path.join(self.data_dir, "BR-Football-Dataset.csv")
        df = pd.read_csv(path)
        out: list[Match] = []
        for row in df.itertuples(index=False):
            tournament = _safe_str(getattr(row, "tournament"))
            home = _safe_str(getattr(row, "home"))
            away = _safe_str(getattr(row, "away"))
            hbase, _ = norm.normalize_team(home)
            abase, _ = norm.normalize_team(away)
            stats = {
                "home_corner": norm.to_int(getattr(row, "home_corner", None)),
                "away_corner": norm.to_int(getattr(row, "away_corner", None)),
                "home_attack": norm.to_int(getattr(row, "home_attack", None)),
                "away_attack": norm.to_int(getattr(row, "away_attack", None)),
                "home_shots": norm.to_int(getattr(row, "home_shots", None)),
                "away_shots": norm.to_int(getattr(row, "away_shots", None)),
                "total_corners": norm.to_int(getattr(row, "total_corners", None)),
                "ht_result": _safe_str(getattr(row, "ht_result", "")),
                "at_result": _safe_str(getattr(row, "at_result", "")),
                "time": _safe_str(getattr(row, "time", "")),
            }
            out.append(Match(
                competition=norm.normalize_competition(tournament) or tournament,
                date=norm.parse_date(getattr(row, "date", None)),
                season=_season_from_date(norm.parse_date(getattr(row, "date", None))),
                home_team=home, away_team=away,
                home_state=None, away_state=None,
                home_goal=norm.to_int(getattr(row, "home_goal", None)),
                away_goal=norm.to_int(getattr(row, "away_goal", None)),
                stage=tournament,
                source_file="BR-Football-Dataset.csv",
                home_key=hbase, away_key=abase,
                stats=stats,
            ))
        return out

    def _load_historical(self) -> list[Match]:
        path = os.path.join(self.data_dir, "novo_campeonato_brasileiro.csv")
        df = pd.read_csv(path)
        out: list[Match] = []
        for row in df.itertuples(index=False):
            home = _safe_str(getattr(row, "Equipe_mandante"))
            away = _safe_str(getattr(row, "Equipe_visitante"))
            hbase, _ = norm.normalize_team(home)
            abase, _ = norm.normalize_team(away)
            stats = {
                "arena": _safe_str(getattr(row, "Arena", "")),
                "winner": _safe_str(getattr(row, "Vencedor", "")),
                "home_uf": _safe_str(getattr(row, "Mandante_UF", "")),
                "away_uf": _safe_str(getattr(row, "Visitante_UF", "")),
            }
            out.append(Match(
                competition="Brasileirão (Historical)",
                date=norm.parse_date(getattr(row, "Data", None)),
                season=norm.to_int(getattr(row, "Ano", None)),
                home_team=home, away_team=away,
                home_state=_safe_str(getattr(row, "Mandante_UF", "")) or None,
                away_state=_safe_str(getattr(row, "Visitante_UF", "")) or None,
                home_goal=norm.to_int(getattr(row, "Gols_mandante", None)),
                away_goal=norm.to_int(getattr(row, "Gols_visitante", None)),
                stage=f"Round {getattr(row, 'Rodada', '')}",
                source_file="novo_campeonato_brasileiro.csv",
                home_key=hbase, away_key=abase,
                stats=stats,
            ))
        return out

    def _load_players(self) -> None:
        path = os.path.join(self.data_dir, "fifa_data.csv")
        df = pd.read_csv(path)
        # Skill columns are everything numeric after the identity columns; we
        # capture a small, useful attribute subset rather than all 60+.
        skill_cols = [
            "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing",
            "Volleys", "Dribbling", "Curve", "FKAccuracy", "LongPassing",
            "BallControl", "Acceleration", "SprintSpeed", "Agility",
            "Reactions", "Balance", "ShotPower", "Jumping", "Stamina",
            "Strength", "LongShots", "Aggression", "Interceptions",
            "Positioning", "Vision", "Penalties", "Composure", "Marking",
            "StandingTackle", "SlidingTackle",
        ]
        # Use record dicts (not itertuples) so columns whose names contain
        # spaces ("Preferred Foot", "Jersey Number") are addressable verbatim.
        for rec in df.to_dict("records"):
            attrs = {c: norm.to_int(rec.get(c)) for c in skill_cols}
            self.players.append(Player(
                id=int(rec["ID"]),
                name=_safe_str(rec.get("Name")),
                age=norm.to_int(rec.get("Age")),
                nationality=_safe_str(rec.get("Nationality")),
                overall=norm.to_int(rec.get("Overall")),
                potential=norm.to_int(rec.get("Potential")),
                club=_safe_str(rec.get("Club")),
                position=_safe_str(rec.get("Position")),
                jersey=norm.to_int(rec.get("Jersey Number")),
                height=_safe_str(rec.get("Height")),
                weight=_safe_str(rec.get("Weight")),
                value=_safe_str(rec.get("Value")),
                wage=_safe_str(rec.get("Wage")),
                preferred_foot=_safe_str(rec.get("Preferred Foot")),
                attributes=attrs,
            ))

    # -- accessors ---------------------------------------------------------
    def competitions(self) -> list[str]:
        return sorted({m.competition for m in self.matches})

    def seasons(self, competition: Optional[str] = None) -> list[int]:
        seasons = {m.season for m in self.matches
                   if m.season is not None
                   and (competition is None
                        or norm.normalize_competition(competition) == m.competition)}
        return sorted(seasons)

    def team_names(self) -> list[str]:
        """Return a de-duplicated list of display team names."""
        seen: dict[str, str] = {}
        for m in self.matches:
            for key, display in ((m.home_key, m.home_team), (m.away_key, m.away_team)):
                if key and key not in seen:
                    seen[key] = display
        return list(seen.values())


def _season_from_date(d) -> Optional[int]:
    return d.year if d is not None else None


def _cup_round_label(rnd) -> str:
    """Human-friendly label for a Copa do Brasil numeric round."""
    try:
        n = int(rnd)
    except (TypeError, ValueError):
        return _safe_str(rnd)
    finals = {8: "Final", 7: "Semifinal", 6: "Quarterfinal", 5: "Round of 16"}
    return finals.get(n, f"Round {n}")


@lru_cache(maxsize=1)
def get_store() -> DataStore:
    """Return a process-wide cached :class:`DataStore` (load once)."""
    return DataStore()
