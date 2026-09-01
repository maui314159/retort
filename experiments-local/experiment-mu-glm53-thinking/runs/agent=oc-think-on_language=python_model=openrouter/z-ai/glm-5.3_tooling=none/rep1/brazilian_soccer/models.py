"""Data models for the unified Brazilian soccer knowledge base."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field


@dataclass(slots=True)
class MatchStats:
    """Extended per-match statistics (BR-Football-Dataset.csv)."""

    home_corners: int | None = None
    away_corners: int | None = None
    home_shots: int | None = None
    away_shots: int | None = None
    home_attacks: int | None = None
    away_attacks: int | None = None
    home_halftime: int | None = None
    away_halftime: int | None = None

    def as_dict(self) -> dict:
        return {
            "corners": {"home": self.home_corners, "away": self.away_corners},
            "shots": {"home": self.home_shots, "away": self.away_shots},
            "attacks": {"home": self.home_attacks, "away": self.away_attacks},
            "half_time": (
                f"{self.home_halftime}-{self.away_halftime}"
                if self.home_halftime is not None and self.away_halftime is not None
                else None
            ),
        }


@dataclass(slots=True)
class Match:
    """A single match, normalized across all source files."""

    competition: str
    season: int | None
    home: str  # canonical team key
    away: str
    home_goals: int | None
    away_goals: int | None
    date: dt.date | None = None
    time: str | None = None
    stage: str | None = None
    round_number: int | None = None
    venue: str | None = None
    source: str = ""
    stats: MatchStats | None = None

    @property
    def played(self) -> bool:
        return self.home_goals is not None and self.away_goals is not None

    def goal_pair(self) -> tuple[int, int] | None:
        """(home_goals, away_goals) or None when the score is unknown."""
        if self.home_goals is None or self.away_goals is None:
            return None
        return self.home_goals, self.away_goals

    @property
    def result(self) -> str | None:
        """'home' | 'away' | 'draw' from the home team's perspective."""
        if self.home_goals is None or self.away_goals is None:
            return None
        if self.home_goals > self.away_goals:
            return "home"
        if self.home_goals < self.away_goals:
            return "away"
        return "draw"

    def score(self) -> str:
        if self.played:
            return f"{self.home_goals}-{self.away_goals}"
        return "vs"

    def as_dict(self) -> dict:
        from .normalize import display_name

        payload: dict[str, object] = {
            "date": self.date.isoformat() if self.date else None,
            "time": self.time,
            "competition": self.competition,
            "season": self.season,
            "home": display_name(self.home),
            "away": display_name(self.away),
            "home_goals": self.home_goals,
            "away_goals": self.away_goals,
            "score": self.score(),
            "result": self.result,
            "round": self.round_number,
            "stage": self.stage,
            "venue": self.venue,
            "source": self.source,
        }
        if self.stats:
            payload["stats"] = self.stats.as_dict()
        return payload


@dataclass(slots=True)
class Player:
    """A FIFA-database player record."""

    player_id: int
    name: str
    age: int | None
    nationality: str
    overall: int
    potential: int
    club: str | None
    position: str | None
    jersey_number: int | None
    height: str | None
    weight: str | None
    preferred_foot: str | None
    value_eur: int | None = None
    skills: dict[str, int] = field(default_factory=dict)

    def as_dict(self, include_skills: bool = False) -> dict:
        payload = {
            "id": self.player_id,
            "name": self.name,
            "age": self.age,
            "nationality": self.nationality,
            "overall": self.overall,
            "potential": self.potential,
            "club": self.club or "Free agent",
            "position": self.position or None,
            "jersey_number": self.jersey_number,
            "height": self.height,
            "weight": self.weight,
            "preferred_foot": self.preferred_foot,
            "value_eur": self.value_eur,
        }
        if include_skills:
            payload["skills"] = self.skills
        return payload
