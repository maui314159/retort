"""Data models shared across the Brazilian soccer MCP server.

Context: the repository layer loads ~42k raw CSV rows into these plain
dataclasses once at startup; every MCP tool answers questions by filtering
and aggregating in-memory instances. Matches carry resolved team entity
ids plus the original display spellings, players carry both the raw FIFA
row and a normalised club key so that player and match data can be joined
across files.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

POSITION_GROUPS = {
    "GK": "goalkeeper",
    "LB": "defender", "LWB": "defender", "RB": "defender", "RWB": "defender",
    "CB": "defender", "LCB": "defender", "RCB": "defender",
    "CDM": "midfielder", "LDM": "midfielder", "RDM": "midfielder",
    "CM": "midfielder", "LCM": "midfielder", "RCM": "midfielder",
    "CAM": "midfielder", "LAM": "midfielder", "RAM": "midfielder",
    "LM": "midfielder", "RM": "midfielder",
    "LW": "forward", "RW": "forward", "LF": "forward", "RF": "forward",
    "LS": "forward", "RS": "forward", "ST": "forward", "CF": "forward",
}

LIBERTADORES_STAGE_ORDER = {
    "group stage": 0,
    "round of 16": 1,
    "quarterfinals": 2,
    "semifinals": 3,
    "final": 4,
}


def position_group(position: str | None) -> str:
    """Map a FIFA position code to goalkeeper/defender/midfielder/forward."""
    if not position:
        return "unknown"
    return POSITION_GROUPS.get(position.strip().upper(), "unknown")


@dataclass
class Match:
    """One played match, normalised across the six source files."""

    date: date
    competition: str
    season: int
    home_team: str
    away_team: str
    home_display: str
    away_display: str
    home_goals: int
    away_goals: int
    time: str | None = None
    round: int | None = None
    stage: str | None = None
    stadium: str | None = None
    source: str = ""
    home_corners: int | None = None
    away_corners: int | None = None
    home_shots: int | None = None
    away_shots: int | None = None
    home_attacks: int | None = None
    away_attacks: int | None = None
    home_ht_goals: int | None = None
    away_ht_goals: int | None = None

    @property
    def outcome(self) -> str:
        """Return "home", "away" or "draw" for the match result."""
        if self.home_goals > self.away_goals:
            return "home"
        if self.away_goals > self.home_goals:
            return "away"
        return "draw"

    @property
    def stage_order(self) -> int:
        return LIBERTADORES_STAGE_ORDER.get(self.stage or "", 99)

    @property
    def sort_key(self):
        return (self.date, self.time or "", self.competition, self.stage_order)

    @property
    def margin(self) -> int:
        return abs(self.home_goals - self.away_goals)

    def to_dict(self) -> dict:
        payload = {
            "date": self.date.isoformat(),
            "time": self.time,
            "competition": self.competition,
            "season": self.season,
            "home_team": self.home_display,
            "away_team": self.away_display,
            "home_goals": self.home_goals,
            "away_goals": self.away_goals,
            "round": self.round,
            "stage": self.stage,
            "stadium": self.stadium,
            "source": self.source,
        }
        extras = {
            "home_corners": self.home_corners,
            "away_corners": self.away_corners,
            "home_shots": self.home_shots,
            "away_shots": self.away_shots,
            "home_attacks": self.home_attacks,
            "away_attacks": self.away_attacks,
        }
        payload.update({k: v for k, v in extras.items() if v is not None})
        return payload


@dataclass
class TeamEntity:
    """A real-world club resolved from all of its spelling variants."""

    key: str
    display: str
    variants: list[str] = field(default_factory=list)
    qualifiers: set = field(default_factory=set)

    def to_dict(self) -> dict:
        return {
            "team": self.display,
            "key": self.key,
            "also_seen_as": self.variants[:8],
        }


@dataclass
class Player:
    """One row of the FIFA player database."""

    fifa_id: int
    name: str
    age: int | None
    nationality: str
    overall: int | None
    potential: int | None
    club: str
    club_key: str
    position: str | None
    position_group: str
    jersey: int | None
    height: str | None
    weight: str | None
    preferred_foot: str | None
    value: str | None
    wage: str | None
    attributes: dict = field(default_factory=dict)

    def to_dict(self, detailed: bool = False) -> dict:
        payload = {
            "id": self.fifa_id,
            "name": self.name,
            "age": self.age,
            "nationality": self.nationality,
            "overall": self.overall,
            "potential": self.potential,
            "club": self.club,
            "position": self.position,
            "position_group": self.position_group,
            "jersey_number": self.jersey,
        }
        if detailed:
            payload.update(
                {
                    "height": self.height,
                    "weight": self.weight,
                    "preferred_foot": self.preferred_foot,
                    "value": self.value,
                    "wage": self.wage,
                    "attributes": self.attributes,
                }
            )
        return payload
