"""Data models for the Brazilian soccer knowledge base."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Match:
    """A single football match from any of the provided datasets."""

    date: date | None
    season: int | None
    competition: str  # canonical competition name, e.g. "Brasileirão Série A"
    stage: str | None  # round / stage label, e.g. "Round 22", "final"
    home: str  # canonical team id, e.g. "flamengo-rj"
    away: str
    home_goals: int | None
    away_goals: int | None
    venue: str | None
    source: str  # originating csv file name
    home_corners: int | None = None
    away_corners: int | None = None
    home_shots: int | None = None
    away_shots: int | None = None
    home_attacks: int | None = None
    away_attacks: int | None = None

    @property
    def total_goals(self) -> int | None:
        if self.home_goals is None or self.away_goals is None:
            return None
        return self.home_goals + self.away_goals

    @property
    def goal_margin(self) -> int | None:
        if self.home_goals is None or self.away_goals is None:
            return None
        return abs(self.home_goals - self.away_goals)

    @property
    def has_result(self) -> bool:
        return self.home_goals is not None and self.away_goals is not None

    def winner(self) -> str | None:
        """Canonical team id of the winner, or None for a draw / unknown result."""
        if not self.has_result:
            return None
        if self.home_goals > self.away_goals:
            return self.home
        if self.away_goals > self.home_goals:
            return self.away
        return None

    def to_dict(self, display) -> dict:
        """JSON-serialisable view; ``display`` maps team id -> display name."""

        def _d(team_id: str) -> str:
            return display(team_id)

        return {
            "date": self.date.isoformat() if self.date else None,
            "season": self.season,
            "competition": self.competition,
            "stage": self.stage,
            "home_team": _d(self.home),
            "away_team": _d(self.away),
            "home_goals": self.home_goals,
            "away_goals": self.away_goals,
            "venue": self.venue,
            "source": self.source,
        }


# Curated FIFA attribute columns worth exposing per player.
SKILL_COLUMNS = [
    "Crossing",
    "Finishing",
    "HeadingAccuracy",
    "ShortPassing",
    "Volleys",
    "Dribbling",
    "Curve",
    "FKAccuracy",
    "LongPassing",
    "BallControl",
    "Acceleration",
    "SprintSpeed",
    "Agility",
    "Reactions",
    "Balance",
    "ShotPower",
    "Jumping",
    "Stamina",
    "Strength",
    "LongShots",
    "Aggression",
    "Interceptions",
    "Positioning",
    "Vision",
    "Penalties",
    "Composure",
    "Marking",
    "StandingTackle",
    "SlidingTackle",
    "GKDiving",
    "GKHandling",
    "GKKicking",
    "GKPositioning",
    "GKReflexes",
]


@dataclass
class Player:
    """A player from the FIFA dataset."""

    player_id: int
    name: str
    age: int | None
    nationality: str
    overall: int
    potential: int | None
    club: str  # raw club string from the dataset
    position: str | None
    jersey_number: int | None
    preferred_foot: str | None
    value: str | None  # raw market value string, e.g. "€110.5M"
    wage: str | None  # raw wage string
    height: str | None
    weight: str | None
    skills: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        out = {
            "id": self.player_id,
            "name": self.name,
            "age": self.age,
            "nationality": self.nationality,
            "overall": self.overall,
            "potential": self.potential,
            "club": self.club,
            "position": self.position,
            "jersey_number": self.jersey_number,
            "preferred_foot": self.preferred_foot,
        }
        if self.value:
            out["value"] = self.value
        if self.wage:
            out["wage"] = self.wage
        if self.height:
            out["height"] = self.height
        if self.weight:
            out["weight"] = self.weight
        if self.skills:
            out["skills"] = dict(self.skills)
        return out
