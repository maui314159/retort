"""Core data models for matches and players."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Match:
    """A single football match across any of the datasets."""

    date: date
    home: str  # normalized team key
    away: str  # normalized team key
    home_goals: int
    away_goals: int
    competition: str  # canonical competition name
    season: int | None = None
    round: str | None = None  # round number, cup round or stage name
    venue: str | None = None
    stats: dict = field(default_factory=dict)  # corners/shots/attacks when known

    def winner(self) -> str | None:
        """Normalized key of the winning team, or None for a draw."""
        if self.home_goals > self.away_goals:
            return self.home
        if self.away_goals > self.home_goals:
            return self.away
        return None

    def total_goals(self) -> int:
        return self.home_goals + self.away_goals

    def involves(self, team_key: str) -> bool:
        return team_key in (self.home, self.away)

    def to_dict(self) -> dict:
        return {
            "date": self.date.isoformat(),
            "home": self.home,
            "away": self.away,
            "home_goals": self.home_goals,
            "away_goals": self.away_goals,
            "competition": self.competition,
            "season": self.season,
            "round": self.round,
            "venue": self.venue,
        }


@dataclass(frozen=True)
class Player:
    """A FIFA-database player record."""

    id: int
    name: str
    age: int | None
    nationality: str
    overall: int
    potential: int
    club: str | None
    position: str | None
    jersey_number: int | None
    nationality_key: str
    club_key: str | None
    name_key: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "age": self.age,
            "nationality": self.nationality,
            "overall": self.overall,
            "potential": self.potential,
            "club": self.club,
            "position": self.position,
            "jersey_number": self.jersey_number,
        }
