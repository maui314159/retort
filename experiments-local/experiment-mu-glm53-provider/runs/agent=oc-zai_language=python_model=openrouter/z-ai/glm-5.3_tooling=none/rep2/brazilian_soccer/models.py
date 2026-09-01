"""Data models for matches, players, and league table records."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Match:
    """A single football match from one of the source datasets."""

    date: date | None
    home: str
    away: str
    home_goals: int | None
    away_goals: int | None
    season: int | None
    competition: str
    source: str
    stage: str | None = None
    round: str | None = None
    extras: dict = field(default_factory=dict, compare=False)

    @property
    def is_scored(self) -> bool:
        return self.home_goals is not None and self.away_goals is not None

    def involves(self, team: str) -> bool:
        return team in (self.home, self.away)

    def goals_for(self, team: str) -> int | None:
        if not self.is_scored:
            return None
        if team == self.home:
            return self.home_goals
        if team == self.away:
            return self.away_goals
        return None

    def result_for(self, team: str) -> str | None:
        """Return 'W', 'L', 'D' for the given team, or None when unknown."""
        if not self.is_scored or not self.involves(team):
            return None
        own = self.goals_for(team)
        opp = self.away_goals if team == self.home else self.home_goals
        if own > opp:
            return "W"
        if own < opp:
            return "L"
        return "D"

    @property
    def margin(self) -> int | None:
        if not self.is_scored:
            return None
        return abs(self.home_goals - self.away_goals)

    @property
    def winner(self) -> str | None:
        if not self.is_scored:
            return None
        if self.home_goals > self.away_goals:
            return self.home
        if self.away_goals > self.home_goals:
            return self.away
        return None

    def sort_key(self) -> tuple:
        return (
            self.date.isoformat() if self.date else "9999-99-99",
            self.competition,
            self.home,
            self.away,
        )


@dataclass(frozen=True)
class Player:
    """A player from the FIFA dataset."""

    id: int | None
    name: str
    age: int | None
    nationality: str
    overall: int | None
    potential: int | None
    club: str | None
    club_key: str | None
    position: str
    jersey: int | None
    height: str
    weight: str
    foot: str
    skills: dict = field(default_factory=dict, compare=False)


@dataclass
class TeamRecord:
    """Aggregated win/draw/loss record for one team over a set of matches."""

    team: str
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0

    def add_match(self, match: Match) -> None:
        if not match.is_scored or not match.involves(self.team):
            return
        self.played += 1
        own = match.goals_for(self.team)
        opp = match.away_goals if match.home == self.team else match.home_goals
        self.goals_for += own
        self.goals_against += opp
        result = match.result_for(self.team)
        if result == "W":
            self.wins += 1
        elif result == "D":
            self.draws += 1
        else:
            self.losses += 1

    @property
    def points(self) -> int:
        return self.wins * 3 + self.draws

    @property
    def goal_diff(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def win_rate(self) -> float | None:
        if self.played == 0:
            return None
        return self.wins / self.played
