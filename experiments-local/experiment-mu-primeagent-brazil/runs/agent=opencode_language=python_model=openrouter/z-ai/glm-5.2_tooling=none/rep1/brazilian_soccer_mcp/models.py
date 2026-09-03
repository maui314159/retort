"""Data models for the Brazilian soccer knowledge graph.

The models are intentionally light (``dataclass`` based) so that the whole
dataset fits comfortably in memory and can be queried without external
database dependencies, satisfying the "no timeout" success criterion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Match:
    """A single match record normalised across the five match CSV files."""

    date: date | None
    home: str
    away: str
    home_display: str
    away_display: str
    home_goal: int
    away_goal: int
    competition: str
    season: int | None
    round: str | None = None
    stage: str | None = None
    venue: str | None = None
    source: str = ""
    extras: dict = field(default_factory=dict)

    @property
    def total_goals(self) -> int:
        return (self.home_goal or 0) + (self.away_goal or 0)

    @property
    def goal_difference(self) -> int:
        return abs((self.home_goal or 0) - (self.away_goal or 0))

    def involves(self, team: str) -> bool:
        return team in (self.home, self.away)

    def winner(self) -> str | None:
        """Return the canonical key of the winning team, or None for a draw."""
        if self.home_goal > self.away_goal:
            return self.home
        if self.away_goal > self.home_goal:
            return self.away
        return None


@dataclass(frozen=True)
class Player:
    """A FIFA player record (subset of the full fifa_data.csv schema)."""

    id: int | None
    name: str
    age: int | None
    nationality: str
    overall: int | None
    potential: int | None
    club: str
    position: str | None
    jersey: int | None
    height: str | None
    weight: str | None
    preferred_foot: str | None
    value: str | None
    wage: str | None
    attributes: dict = field(default_factory=dict)
