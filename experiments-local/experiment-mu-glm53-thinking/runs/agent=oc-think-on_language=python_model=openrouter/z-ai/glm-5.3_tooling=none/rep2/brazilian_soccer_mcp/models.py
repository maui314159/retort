"""Core domain models for the Brazilian Soccer MCP server.

Two frozen dataclasses carry all query results:

- :class:`Match` — one row from any of the five match datasets, with team
  names canonicalised, dates parsed and extended statistics (corners, shots,
  attacks) carried when the source dataset provides them.
- :class:`Player` — one row of the FIFA player dataset.

Both expose ``to_dict()`` so the MCP layer can serialise them as JSON.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Optional

WIN = "W"
DRAW = "D"
LOSS = "L"


@dataclass(frozen=True)
class Match:
    """A single soccer match from any of the provided datasets."""

    competition: str
    season: Optional[int]
    home_team: str
    away_team: str
    home_goals: Optional[int]
    away_goals: Optional[int]
    date: Optional[date] = None
    time: Optional[str] = None
    round: Optional[str] = None
    stage: Optional[str] = None
    venue: Optional[str] = None
    source: str = ""
    home_corners: Optional[int] = None
    away_corners: Optional[int] = None
    home_shots: Optional[int] = None
    away_shots: Optional[int] = None
    home_attacks: Optional[int] = None
    away_attacks: Optional[int] = None

    @property
    def is_played(self) -> bool:
        """True when both scores are known (i.e. the match has a result)."""
        return self.home_goals is not None and self.away_goals is not None

    @property
    def total_goals(self) -> Optional[int]:
        if not self.is_played:
            return None
        return self.home_goals + self.away_goals

    @property
    def goal_margin(self) -> Optional[int]:
        """Absolute goal difference (for biggest-win rankings)."""
        if not self.is_played:
            return None
        return abs(self.home_goals - self.away_goals)

    def score_display(self) -> str:
        if not self.is_played:
            return "vs"
        return f"{self.home_goals}-{self.away_goals}"

    def result_for(self, team: str) -> Optional[str]:
        """Return 'W', 'D' or 'L' from ``team``'s perspective."""
        if not self.is_played:
            return None
        if team not in (self.home_team, self.away_team):
            return None
        if self.home_goals == self.away_goals:
            return DRAW
        home_won = self.home_goals > self.away_goals
        if team == self.home_team:
            return WIN if home_won else LOSS
        return LOSS if home_won else WIN

    def winner(self) -> Optional[str]:
        """Canonical name of the winning team, or None for draws/missing data."""
        if not self.is_played or self.home_goals == self.away_goals:
            return None
        return self.home_team if self.home_goals > self.away_goals else self.away_team

    def involves(self, team: str) -> bool:
        return team in (self.home_team, self.away_team)

    def with_stats(self, **stats: Any) -> "Match":
        """Return a copy enriched with extended statistics."""
        return replace(self, **stats)

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date.isoformat() if self.date else None,
            "time": self.time,
            "competition": self.competition,
            "season": self.season,
            "round": self.round,
            "stage": self.stage,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_goals": self.home_goals,
            "away_goals": self.away_goals,
            "score": self.score_display(),
            "venue": self.venue,
            "source": self.source,
            "stats": {
                "home_corners": self.home_corners,
                "away_corners": self.away_corners,
                "home_shots": self.home_shots,
                "away_shots": self.away_shots,
                "home_attacks": self.home_attacks,
                "away_attacks": self.away_attacks,
            },
        }

    def summary_line(self) -> str:
        """One-line human readable rendering used in formatted answers."""
        when = self.date.isoformat() if self.date else "unknown date"
        tag = self.round or self.stage
        comp = self.competition + (f" {tag}" if tag else "")
        return f"{when}: {self.home_team} {self.score_display()} {self.away_team} ({comp})"


@dataclass(frozen=True)
class Player:
    """A player from the FIFA dataset."""

    id: int
    name: str
    age: Optional[int]
    nationality: Optional[str]
    overall: Optional[int]
    potential: Optional[int]
    club: Optional[str]
    position: Optional[str]
    jersey_number: Optional[int]
    preferred_foot: Optional[str] = None
    value_eur: Optional[int] = None
    wage_eur: Optional[int] = None
    skills: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
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
            "preferred_foot": self.preferred_foot,
            "value_eur": self.value_eur,
            "wage_eur": self.wage_eur,
            "skills": dict(sorted(self.skills.items())),
        }
