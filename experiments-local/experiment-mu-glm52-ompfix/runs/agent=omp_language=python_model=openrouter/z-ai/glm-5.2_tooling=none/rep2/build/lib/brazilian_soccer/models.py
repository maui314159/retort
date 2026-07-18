# brazilian_soccer.models
# -----------------------------------------------------------------------------
# Context:
#   Lightweight, serializable dataclasses describing the entities the MCP server
#   reasons about. They are the contract between the data layer (loader.py),
#   the query layer (queries.py) and the MCP tools (server.py). Every field is
#   JSON-serializable so the MCP layer can return these objects verbatim.
#
#   The models are intentionally narrow: they carry only the fields needed to
#   answer the query categories in TASK.md (matches, teams, players,
#   competitions, statistics). Match-level advanced stats (corners/shots/attacks)
#   are optional and only present for rows sourced from BR-Football-Dataset.csv.
# -----------------------------------------------------------------------------
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Match:
    """A single football match across any of the bundled competitions."""

    date: str | None            # ISO date (YYYY-MM-DD); None if unparseable
    competition: str            # canonical competition name
    season: int | None          # year of the season
    home_team: str              # normalized display name
    away_team: str              # normalized display name
    home_goal: int | None       # full-time goals; None if missing
    away_goal: int | None
    round: str | None           # league round number, cup round, or stage
    stage: str | None           # Libertadores stage (group/knockout/final ...)
    venue: str | None           # stadium, when known (historical dataset)
    source: str                 # which CSV file produced this row
    home_corner: float | None = None
    away_corner: float | None = None
    home_shots: float | None = None
    away_shots: float | None = None
    home_attack: float | None = None
    away_attack: float | None = None
    total_corners: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TeamRecord:
    """A team's record over a filtered set of matches."""

    team: str
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def points(self) -> int:
        return 3 * self.wins + self.draws

    @property
    def win_rate(self) -> float:
        return round(self.wins / self.played, 4) if self.played else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "team": self.team,
            "played": self.played,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses,
            "goals_for": self.goals_for,
            "goals_against": self.goals_against,
            "goal_difference": self.goal_difference,
            "points": self.points,
            "win_rate": self.win_rate,
        }


@dataclass
class Standing:
    """One row of a competition table (calculated from match results)."""

    position: int
    team: str
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Player:
    """A FIFA player row, projected to the fields the queries need."""

    id: int | None
    name: str
    age: int | None
    nationality: str
    overall: int | None
    potential: int | None
    club: str
    position: str
    jersey_number: int | None
    height: str | None
    weight: str | None
    value: str | None
    wage: str | None
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Canonical competition names used throughout the query layer. The raw datasets
# use a mix of spellings ("Serie A", "Serie B", "Copa do Brasil", ...); the
# loader maps every row onto one of these.
COMPETITIONS = {
    "BRASILEIRAO_SERIE_A": "Brasileirão Série A",
    "BRASILEIRAO_SERIE_B": "Brasileirão Série B",
    "BRASILEIRAO_SERIE_C": "Brasileirão Série C",
    "COPA_DO_BRASIL": "Copa do Brasil",
    "COPA_LIBERTADORES": "Copa Libertadores",
}

# Forward position codes grouped into outfield roles. Used by player queries
# like "show me all forwards from São Paulo FC".
POSITION_GROUPS: dict[str, set[str]] = {
    "GK": {"GK"},
    "DEF": {"CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"},
    "MID": {"CDM", "CM", "CAM", "LM", "RM", "LCM", "RCM", "LAM", "RAM",
            "LDM", "RDM"},
    "FWD": {"ST", "LS", "RS", "LW", "RW", "LF", "RF", "CF"},
}
