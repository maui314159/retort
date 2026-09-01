"""Data models shared across the Brazilian Soccer MCP server."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass(frozen=True, slots=True)
class Match:
    """A single soccer match from any of the provided datasets."""

    date: Optional[date]
    time: Optional[str]
    home_display: str
    away_display: str
    home_key: str
    away_key: str
    home_goals: Optional[int]
    away_goals: Optional[int]
    competition: str
    season: Optional[int]
    round: Optional[str]
    stage: Optional[str]
    venue: Optional[str]
    source: str
    match_id: Optional[str] = None
    home_corners: Optional[int] = None
    away_corners: Optional[int] = None
    home_shots: Optional[int] = None
    away_shots: Optional[int] = None
    home_attacks: Optional[int] = None
    away_attacks: Optional[int] = None

    @property
    def played(self) -> bool:
        return self.home_goals is not None and self.away_goals is not None

    @property
    def margin(self) -> Optional[int]:
        if not self.played:
            return None
        return abs(self.home_goals - self.away_goals)

    @property
    def winner_key(self) -> Optional[str]:
        if not self.played:
            return None
        if self.home_goals > self.away_goals:
            return self.home_key
        if self.away_goals > self.home_goals:
            return self.away_key
        return None

    @property
    def total_goals(self) -> Optional[int]:
        if not self.played:
            return None
        return self.home_goals + self.away_goals


@dataclass(frozen=True, slots=True)
class Player:
    """A player record from the FIFA player database."""

    player_id: int
    name: str
    name_norm: str
    age: Optional[int]
    nationality: str
    overall: int
    potential: int
    club_display: Optional[str]
    club_key: Optional[str]
    position: Optional[str]
    jersey_number: Optional[str]
    preferred_foot: Optional[str]
    value: Optional[str]
    wage: Optional[str]
    height: Optional[str]
    weight: Optional[str]
    international_reputation: Optional[int]
    skills: dict = field(default_factory=dict)


@dataclass(slots=True)
class TeamStats:
    """Aggregated win/draw/loss statistics for one team over a match set."""

    team_key: str
    team_display: str
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

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against


@dataclass(slots=True)
class StandingRow:
    """One row of a calculated league table."""

    position: int
    team_key: str
    team_display: str
    matches: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    points: int

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against


@dataclass(slots=True)
class HeadToHead:
    """Head-to-head aggregation between two teams."""

    team_a_key: str
    team_a_display: str
    team_b_key: str
    team_b_display: str
    team_a_wins: int = 0
    team_b_wins: int = 0
    draws: int = 0
    goals_a: int = 0
    goals_b: int = 0
    matches: list = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.team_a_wins + self.team_b_wins + self.draws


@dataclass(slots=True)
class CompetitionStats:
    """Aggregate statistics over a set of played matches."""

    matches: int
    goals: int
    avg_goals: float
    home_wins: int
    draws: int
    away_wins: int
    home_win_rate: float
    draw_rate: float
    away_win_rate: float
    avg_home_goals: float
    avg_away_goals: float
    biggest_home_win: Optional[Match] = None
    biggest_away_win: Optional[Match] = None
