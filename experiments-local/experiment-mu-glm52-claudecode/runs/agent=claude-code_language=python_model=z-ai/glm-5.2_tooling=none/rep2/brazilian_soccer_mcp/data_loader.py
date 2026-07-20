"""Load the six Kaggle CSV datasets into unified records + a knowledge graph.

Context
-------
TASK.md enumerates six CSV files in ``data/kaggle/``:

1. ``Brasileirao_Matches.csv``      - Brasileirão Serie A (2012-2022)
2. ``Brazilian_Cup_Matches.csv``   - Copa do Brasil (2012+)
3. ``Libertadores_Matches.csv``    - Copa Libertadores
4. ``BR-Football-Dataset.csv``     - Extended match statistics
5. ``novo_campeonato_brasileiro.csv`` - Historical Brasileirão (2003-2019)
6. ``fifa_data.csv``               - FIFA player database

Each file uses different column names and date formats (see ``normalize.py``).
This module turns them into a single ``Match`` dataclass shape and a single
``Player`` dataclass shape, then wires them into a ``KnowledgeGraph`` so the
query layer can walk team/player/match/competition relationships.

Abrasileirão, Copa do Brasil, Libertadores, Serie B, Serie C and the historical
Brasileirão are all mapped onto stable competition names so the query layer can
filter by ``competition`` regardless of which file the match came from.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

from .graph import KnowledgeGraph
from .normalize import normalize_team, parse_date, parse_int, team_key

# Resolve the data directory relative to the repository root.
DATA_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "kaggle")
)

# Stable competition names used across all queries.
COMP_BRASILEIRAO = "Brasileirão"
COMP_CUP = "Copa do Brasil"
COMP_LIBERTADORES = "Copa Libertadores"
COMP_SERIE_B = "Serie B"
COMP_SERIE_C = "Serie C"


@dataclass
class Match:
    """A single match from any of the match CSV files."""

    match_id: str
    competition: str
    season: Optional[int]
    date: Optional[Any]  # datetime.date
    home_team: str  # normalized display name
    home_team_key: str
    away_team: str
    away_team_key: str
    home_goal: Optional[int]
    away_goal: Optional[int]
    round_: Optional[str] = None
    stage: Optional[str] = None
    arena: Optional[str] = None
    source_file: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    def result_sign(self) -> str:
        """``home`` / ``away`` / ``draw`` or ``unknown`` (when scores missing)."""
        if self.home_goal is None or self.away_goal is None:
            return "unknown"
        if self.home_goal > self.away_goal:
            return "home"
        if self.home_goal < self.away_goal:
            return "away"
        return "draw"

    def winner_key(self) -> Optional[str]:
        sign = self.result_sign()
        if sign == "home":
            return self.home_team_key
        if sign == "away":
            return self.away_team_key
        return None


@dataclass
class Player:
    """A single FIFA player record."""

    id: str
    name: str
    age: Optional[int]
    nationality: str
    overall: Optional[int]
    potential: Optional[int]
    club: str
    position: Optional[str]
    jersey_number: Optional[int]
    height: Optional[str]
    weight: Optional[str]
    attributes: Dict[str, Any] = field(default_factory=dict)


class DataLoader:
    """Load all CSV datasets into ``Match``/``Player`` records + a graph."""

    def __init__(self, data_dir: Optional[str] = None) -> None:
        self.data_dir = data_dir or DATA_DIR
        self.matches: List[Match] = []
        self.players: List[Player] = []
        self.graph = KnowledgeGraph()

    # -- public API ----------------------------------------------------------

    def load_all(self) -> "DataLoader":
        """Load every dataset, build records and wire the knowledge graph."""
        self._load_brasileirao()
        self._load_cup()
        self._load_libertadores()
        self._load_br_football()
        self._load_historical_brasileirao()
        self._load_fifa()
        self._build_graph()
        return self

    # -- match file loaders --------------------------------------------------

    def _load_brasileirao(self) -> None:
        path = os.path.join(self.data_dir, "Brasileirao_Matches.csv")
        df = pd.read_csv(path, encoding="utf-8")
        for i, row in df.iterrows():
            self.matches.append(self._match_from_row(
                row, i, COMP_BRASILEIRAO, "Brasileirao_Matches.csv",
                home_col="home_team", away_col="away_team",
                hg_col="home_goal", ag_col="away_goal",
                season_col="season", round_col="round", date_col="datetime",
            ))

    def _load_cup(self) -> None:
        path = os.path.join(self.data_dir, "Brazilian_Cup_Matches.csv")
        df = pd.read_csv(path, encoding="utf-8")
        for i, row in df.iterrows():
            self.matches.append(self._match_from_row(
                row, i, COMP_CUP, "Brazilian_Cup_Matches.csv",
                home_col="home_team", away_col="away_team",
                hg_col="home_goal", ag_col="away_goal",
                season_col="season", round_col="round", date_col="datetime",
            ))

    def _load_libertadores(self) -> None:
        path = os.path.join(self.data_dir, "Libertadores_Matches.csv")
        df = pd.read_csv(path, encoding="utf-8")
        for i, row in df.iterrows():
            self.matches.append(self._match_from_row(
                row, i, COMP_LIBERTADORES, "Libertadores_Matches.csv",
                home_col="home_team", away_col="away_team",
                hg_col="home_goal", ag_col="away_goal",
                season_col="season", date_col="datetime",
                stage_col="stage",
            ))

    def _load_br_football(self) -> None:
        path = os.path.join(self.data_dir, "BR-Football-Dataset.csv")
        df = pd.read_csv(path, encoding="utf-8")
        for i, row in df.iterrows():
            tournament = str(row.get("tournament", "")).strip()
            comp = {
                "Serie A": COMP_BRASILEIRAO,
                "Serie B": COMP_SERIE_B,
                "Serie C": COMP_SERIE_C,
                "Copa do Brasil": COMP_CUP,
            }.get(tournament, tournament)
            extra = {
                "home_corner": row.get("home_corner"),
                "away_corner": row.get("away_corner"),
                "home_shots": row.get("home_shots"),
                "away_shots": row.get("away_shots"),
                "home_attack": row.get("home_attack"),
                "away_attack": row.get("away_attack"),
                "total_corners": row.get("total_corners"),
                "ht_result": row.get("ht_result"),
                "at_result": row.get("at_result"),
            }
            self.matches.append(self._match_from_row(
                row, i, comp, "BR-Football-Dataset.csv",
                home_col="home", away_col="away",
                hg_col="home_goal", ag_col="away_goal",
                date_col="date", extra=extra,
            ))

    def _load_historical_brasileirao(self) -> None:
        path = os.path.join(self.data_dir, "novo_campeonato_brasileiro.csv")
        df = pd.read_csv(path, encoding="utf-8")
        for i, row in df.iterrows():
            home = normalize_team(row.get("Equipe_mandante", ""))
            away = normalize_team(row.get("Equipe_visitante", ""))
            self.matches.append(Match(
                match_id=f"hist-{row.get('ID', i)}",
                competition=COMP_BRASILEIRAO,
                season=parse_int(row.get("Ano")),
                date=parse_date(row.get("Data")),
                home_team=home,
                home_team_key=team_key(home),
                away_team=away,
                away_team_key=team_key(away),
                home_goal=parse_int(row.get("Gols_mandante")),
                away_goal=parse_int(row.get("Gols_visitante")),
                round_=str(row.get("Rodada")) if pd.notna(row.get("Rodada")) else None,
                arena=row.get("Arena") if pd.notna(row.get("Arena")) else None,
                source_file="novo_campeonato_brasileiro.csv",
                extra={"vencedor": row.get("Vencedor")},
            ))

    def _load_fifa(self) -> None:
        path = os.path.join(self.data_dir, "fifa_data.csv")
        df = pd.read_csv(path, encoding="utf-8-sig")
        # Skill/attribute columns to carry through.
        attr_cols = [
            "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
            "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
            "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
            "ShotPower", "Jumping", "Stamina", "Strength", "LongShots",
            "Aggression", "Interceptions", "Positioning", "Vision", "Penalties",
            "Composure", "Marking", "StandingTackle", "SlidingTackle",
        ]
        for _, row in df.iterrows():
            attrs: Dict[str, Any] = {}
            for c in attr_cols:
                v = row.get(c)
                if isinstance(v, (int, float)) and not (isinstance(v, float) and v != v):
                    attrs[c] = v
            self.players.append(Player(
                id=str(row.get("ID")),
                name=str(row.get("Name", "")).strip(),
                age=parse_int(row.get("Age")),
                nationality=str(row.get("Nationality", "")).strip(),
                overall=parse_int(row.get("Overall")),
                potential=parse_int(row.get("Potential")),
                club=str(row.get("Club", "")).strip(),
                position=row.get("Position") if pd.notna(row.get("Position")) else None,
                jersey_number=parse_int(row.get("Jersey Number")),
                height=row.get("Height") if pd.notna(row.get("Height")) else None,
                weight=row.get("Weight") if pd.notna(row.get("Weight")) else None,
                attributes=attrs,
            ))

    # -- helpers -------------------------------------------------------------

    def _match_from_row(
        self,
        row: pd.Series,
        index: int,
        competition: str,
        source_file: str,
        home_col: str,
        away_col: str,
        hg_col: str,
        ag_col: str,
        season_col: Optional[str] = None,
        round_col: Optional[str] = None,
        date_col: Optional[str] = None,
        stage_col: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Match:
        home = normalize_team(row.get(home_col, ""))
        away = normalize_team(row.get(away_col, ""))
        season = parse_int(row.get(season_col)) if season_col else None
        round_ = None
        if round_col and pd.notna(row.get(round_col)):
            round_ = str(row.get(round_col))
        stage = None
        if stage_col and pd.notna(row.get(stage_col)):
            stage = str(row.get(stage_col))
        return Match(
            match_id=f"{source_file}-{index}",
            competition=competition,
            season=season,
            date=parse_date(row.get(date_col)) if date_col else None,
            home_team=home,
            home_team_key=team_key(home),
            away_team=away,
            away_team_key=team_key(away),
            home_goal=parse_int(row.get(hg_col)),
            away_goal=parse_int(row.get(ag_col)),
            round_=round_,
            stage=stage,
            source_file=source_file,
            extra=extra or {},
        )

    # -- graph construction --------------------------------------------------

    def _build_graph(self) -> None:
        g = self.graph
        # Competition nodes.
        for comp in {m.competition for m in self.matches}:
            g.add_node("competition", f"comp:{comp}", comp)
        # Season nodes.
        for m in self.matches:
            if m.season is None:
                continue
            g.add_node("season", f"season:{m.season}", str(m.season), year=m.season)
        # Team nodes (deduped by canonical key, prefer accent-correct display).
        for m in self.matches:
            for name in (m.home_team, m.away_team):
                key = team_key(name)
                if not key:
                    continue
                if key not in g.nodes:
                    g.add_node("team", key, name)
                else:
                    # Prefer a label that retains accents (longest non-stripped).
                    existing = g.nodes[key].label
                    if len(name) > len(existing):
                        g.nodes[key].label = name
        # Match nodes + edges.
        for m in self.matches:
            g.add_node(
                "match", m.match_id, f"{m.home_team} vs {m.away_team}",
                date=m.date.isoformat() if m.date else None,
                competition=m.competition, season=m.season,
                home_goal=m.home_goal, away_goal=m.away_goal,
                round=m.round_, stage=m.stage,
            )
            g.add_edge(m.match_id, f"comp:{m.competition}", "HELD_IN")
            if m.season is not None:
                g.add_edge(m.match_id, f"season:{m.season}", "HELD_IN")
            g.add_edge(m.home_team_key, m.match_id, "PLAYED_IN", side="home")
            g.add_edge(m.away_team_key, m.match_id, "PLAYED_IN", side="away")
            sign = m.result_sign()
            if sign == "home":
                g.add_edge(m.home_team_key, m.match_id, "WON", goals=m.home_goal)
                g.add_edge(m.away_team_key, m.match_id, "LOST", goals=m.away_goal)
            elif sign == "away":
                g.add_edge(m.away_team_key, m.match_id, "WON", goals=m.away_goal)
                g.add_edge(m.home_team_key, m.match_id, "LOST", goals=m.home_goal)
            elif sign == "draw":
                g.add_edge(m.home_team_key, m.match_id, "DREW", goals=m.home_goal)
                g.add_edge(m.away_team_key, m.match_id, "DREW", goals=m.away_goal)
        # Player nodes + PARTICIPATED_IN edges (link to club team if known).
        for p in self.players:
            g.add_node(
                "player", f"player:{p.id}", p.name,
                nationality=p.nationality, overall=p.overall,
                position=p.position, club=p.club,
            )
            club_key = team_key(p.club)
            if club_key in g.nodes:
                g.add_edge(f"player:{p.id}", club_key, "PARTICIPATED_IN", role="club_member")
