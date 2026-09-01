"""
Domain models for the Brazilian Soccer MCP server.

Context (Why): TASK.md requires a "knowledge graph interface" style query layer
over heterogeneous CSV sources. Before any querying is possible the six raw
datasets must be projected onto a small, uniform entity model so that every
query (matches, teams, players, competitions, statistics) works against one
shape of data regardless of which file a row came from.

What (design decisions):
    * Match is a single unified record for all 5 match datasets. Not every
      source has every field, so everything except team ids and competition is
      optional (None) and the service layer degrades gracefully.
    * Teams are referenced by canonical normalized id (see normalizer.py);
      a human-readable display name is snapshotted at load time for cheap
      formatting without a registry lookup.
    * Competition names are canonical, human-facing strings ("Brasileirao
      Serie A" written with accents) shared by loaders and service.
    * Player models the FIFA dataset; skill/position-rating columns are kept
      in an open ``attrs`` mapping because the FIFA CSV exposes ~70 of them
      and only some are ever queried.
    * TeamRecord is the aggregate used by standings / team-record queries:
      wins, draws, losses, goals for/against computed from Match rows.

Test: exercises via tests/test_loaders.py, tests/test_team_queries.py and
tests/test_competition_queries.py (BDD scenarios assert on real data).
Spec reference: TASK.md "Provided Data" tables (column lists per file),
"Required Capabilities" sections 1-5.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Canonical competition names (used across loaders, service and MCP tools)
# ---------------------------------------------------------------------------

BRASILEIRAO_A = "Brasileirão Série A"
BRASILEIRAO_B = "Brasileirão Série B"
BRASILEIRAO_C = "Brasileirão Série C"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"

# Friendly aliases accepted from users/LLMs -> canonical competition name.
COMPETITION_ALIASES: dict[str, str] = {
    "brasileirao": BRASILEIRAO_A,
    "brasileirão": BRASILEIRAO_A,
    "serie a": BRASILEIRAO_A,
    "série a": BRASILEIRAO_A,
    "serie a (brasileirao)": BRASILEIRAO_A,
    "campeonato brasileiro": BRASILEIRAO_A,
    "serie b": BRASILEIRAO_B,
    "série b": BRASILEIRAO_B,
    "serie c": BRASILEIRAO_C,
    "série c": BRASILEIRAO_C,
    "copa do brasil": COPA_DO_BRASIL,
    "brazilian cup": COPA_DO_BRASIL,
    "copa do brasil (brazilian cup)": COPA_DO_BRASIL,
    "libertadores": LIBERTADORES,
    "copa libertadores": LIBERTADORES,
    "libertadores da america": LIBERTADORES,
    "copa libertadores de america": LIBERTADORES,
}


@dataclass(frozen=True)
class Match:
    """One football match, unified across the 5 match CSV datasets."""

    date: Optional[date]                 # kick-off date (time-of-day dropped)
    home_id: str                         # canonical normalized team id
    away_id: str
    home_display: str                    # best display name at load time
    away_display: str
    home_goals: Optional[int]
    away_goals: Optional[int]
    competition: str                     # canonical competition name
    season: Optional[int]
    round_no: Optional[str] = None       # league round / cup round number
    stage: Optional[str] = None          # Libertadores stage ("final", ...)
    venue: Optional[str] = None          # stadium (historical file only)
    source: str = ""                     # originating CSV file name
    # Extended statistics (BR-Football-Dataset.csv only):
    home_corners: Optional[int] = None
    away_corners: Optional[int] = None
    home_shots: Optional[int] = None
    away_shots: Optional[int] = None
    home_attacks: Optional[int] = None
    away_attacks: Optional[int] = None
    half_time_diff: Optional[int] = None     # BR-Football: home HT goals - away HT goals
    half_time_label: Optional[str] = None    # BR-Football: WIN / DRAW / LOSS (home view)

    # -- helpers ------------------------------------------------------------

    def played(self) -> bool:
        """True when both scores are known."""
        return self.home_goals is not None and self.away_goals is not None

    def winner(self) -> Optional[str]:
        """'home', 'away', 'draw' or None when the score is unknown."""
        if not self.played():
            return None
        if self.home_goals > self.away_goals:
            return "home"
        if self.home_goals < self.away_goals:
            return "away"
        return "draw"

    def total_goals(self) -> Optional[int]:
        if not self.played():
            return None
        return self.home_goals + self.away_goals

    def margin(self) -> Optional[int]:
        if not self.played():
            return None
        return abs(self.home_goals - self.away_goals)

    def score_str(self) -> str:
        if self.played():
            return f"{self.home_goals}-{self.away_goals}"
        return "?-?"

    def date_str(self) -> str:
        return self.date.isoformat() if self.date else "unknown date"

    def detail_label(self) -> str:
        """Competition/round/stage annotation used in listings."""
        parts: list[str] = [self.competition]
        if self.round_no:
            parts.append(f"Round {self.round_no}")
        if self.stage:
            parts.append(self.stage)
        if self.venue:
            parts.append(self.venue)
        return " ".join(parts)


@dataclass(frozen=True)
class Player:
    """One FIFA-dataset player row."""

    player_id: int
    name: str
    age: Optional[int]
    nationality: str
    overall: Optional[int]
    potential: Optional[int]
    club: str
    position: Optional[str]
    jersey_number: Optional[int]
    preferred_foot: Optional[str] = None
    height_raw: Optional[str] = None     # e.g. "5'9"
    weight_raw: Optional[str] = None     # e.g. "150lbs"
    height_cm: Optional[int] = None      # parsed from height_raw
    weight_kg: Optional[int] = None      # parsed from weight_raw
    attrs: dict[str, Any] = field(default_factory=dict)  # skill ratings etc.

    @property
    def is_brazilian(self) -> bool:
        return self.nationality.strip().lower() == "brazil"


@dataclass
class TeamRecord:
    """Aggregated W/D/L + goals for one team over a set of matches."""

    team_id: str
    display: str
    matches: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0

    @property
    def points(self) -> int:
        return self.wins * 3 + self.draws

    @property
    def win_rate(self) -> float:
        return self.wins / self.matches if self.matches else 0.0

    def add_match(self, is_home: bool, gf: int, ga: int) -> None:
        self.matches += 1
        self.goals_for += gf
        self.goals_against += ga
        if gf > ga:
            self.wins += 1
        elif gf == ga:
            self.draws += 1
        else:
            self.losses += 1
        _ = is_home  # kept for future home/away split record keeping

    def summary_line(self) -> str:
        return (
            f"{self.matches} matches: {self.wins}W {self.draws}D {self.losses}L, "
            f"GF {self.goals_for}, GA {self.goals_against}"
        )
