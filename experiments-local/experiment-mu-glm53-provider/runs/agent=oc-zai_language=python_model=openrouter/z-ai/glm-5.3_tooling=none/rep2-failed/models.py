"""Domain models for the Brazilian Soccer MCP server.

Defines the two core entities shared by every layer of the system:

* :class:`Match` — a single soccer match, unified across the five match
  datasets (Brasileirão, Copa do Brasil, Libertadores, extended stats,
  historical Brasileirão 2003-2019).
* :class:`Player` — a player from the FIFA dataset.

Both models store *canonical team keys* (see :mod:`normalize`) alongside
the raw display names so that cross-file team matching is reliable even
though every dataset spells club names differently.

The :class:`TeamRecord` value object carries an aggregate win/draw/loss
line for one team over an arbitrary set of matches.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Match:
    """A single soccer match, normalized across all provided datasets."""

    date: date | None
    home_team: str
    away_team: str
    home_goals: int | None
    away_goals: int | None
    competition: str
    season: int | None
    home_key: str
    away_key: str
    round: str | None = None
    stage: str | None = None
    stadium: str | None = None
    kickoff: str | None = None
    home_state: str | None = None
    away_state: str | None = None
    source: str = ""
    stats: dict = field(default_factory=dict)

    @property
    def score(self) -> str | None:
        if self.home_goals is None or self.away_goals is None:
            return None
        return f"{self.home_goals}-{self.away_goals}"

    @property
    def total_goals(self) -> int | None:
        if self.home_goals is None or self.away_goals is None:
            return None
        return self.home_goals + self.away_goals

    def winner_key(self) -> str | None:
        """Canonical key of the winning team, or None for a draw/unknown."""
        if self.home_goals is None or self.away_goals is None:
            return None
        if self.home_goals > self.away_goals:
            return self.home_key
        if self.away_goals > self.home_goals:
            return self.away_key
        return None

    def involves(self, team_key: str) -> bool:
        return team_key in (self.home_key, self.away_key)

    def to_dict(self) -> dict:
        return {
            "date": self.date.isoformat() if self.date else None,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "score": self.score,
            "home_goals": self.home_goals,
            "away_goals": self.away_goals,
            "competition": self.competition,
            "season": self.season,
            "round": self.round,
            "stage": self.stage,
            "stadium": self.stadium,
        }


@dataclass(frozen=True)
class Player:
    """A player from the FIFA dataset."""

    id: str
    name: str
    age: int | None
    nationality: str
    overall: int | None
    potential: int | None
    club: str
    position: str | None
    jersey_number: int | None
    height: str | None
    weight: str | None
    preferred_foot: str | None
    value: str | None
    wage: str | None
    club_key: str
    skills: dict = field(default_factory=dict)

    def to_dict(self, include_skills: bool = False) -> dict:
        base = {
            "id": self.id,
            "name": self.name,
            "age": self.age,
            "nationality": self.nationality,
            "overall": self.overall,
            "potential": self.potential,
            "club": self.club,
            "position": self.position,
            "jersey_number": self.jersey_number,
            "height": self.height,
            "weight": self.weight,
            "preferred_foot": self.preferred_foot,
            "value": self.value,
            "wage": self.wage,
        }
        if include_skills:
            base["skills"] = dict(sorted(self.skills.items()))
        return base


@dataclass
class TeamRecord:
    """Aggregate win/draw/loss line for one team over a set of matches."""

    team_key: str
    matches: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    home_wins: int = 0
    home_draws: int = 0
    home_losses: int = 0
    away_wins: int = 0
    away_draws: int = 0
    away_losses: int = 0

    @property
    def points(self) -> int:
        return self.wins * 3 + self.draws

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def win_rate(self) -> float | None:
        if self.matches == 0:
            return None
        return round(self.wins / self.matches * 100, 1)

    def merge_line(self, prefix: str) -> dict:
        return {
            "matches": getattr(self, f"{prefix}_wins")
            + getattr(self, f"{prefix}_draws")
            + getattr(self, f"{prefix}_losses"),
            "wins": getattr(self, f"{prefix}_wins"),
            "draws": getattr(self, f"{prefix}_draws"),
            "losses": getattr(self, f"{prefix}_losses"),
        }

    def to_dict(self) -> dict:
        return {
            "team": self.team_key,
            "matches": self.matches,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses,
            "goals_for": self.goals_for,
            "goals_against": self.goals_against,
            "goal_difference": self.goal_difference,
            "points": self.points,
            "win_rate_pct": self.win_rate,
            "home": self.merge_line("home"),
            "away": self.merge_line("away"),
        }
