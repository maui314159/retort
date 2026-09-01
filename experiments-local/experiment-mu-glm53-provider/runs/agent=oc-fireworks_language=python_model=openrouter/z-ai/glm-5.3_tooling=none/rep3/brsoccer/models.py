"""Domain models for the Brazilian soccer datasets.

Two record types carry all of the data: :class:`Match` (one row from any
of the five match CSV files, canonicalised) and :class:`Player` (one row
of the FIFA player database). :class:`TableRow` is a computed league
table row used by the standings query.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Match:
    """A single football match, canonicalised across source files.

    Team fields store *canonical registry keys* (see
    :mod:`brsoccer.normalize`); the ``*_display`` twins keep the prettiest
    human-facing spelling. Goals are ``None`` when the source recorded the
    match without a score (``NA`` / ``-``).
    """

    date: date | None
    date_text: str
    competition: str  # registry code, e.g. "serie_a"
    competition_display: str  # e.g. "Brasileirão Série A"
    season: int | None
    stage: str  # round number ("22") or cup stage ("final")
    home: str
    away: str
    home_display: str
    away_display: str
    home_goal: int | None = None
    away_goal: int | None = None
    kickoff: str | None = None  # "18:30:00" when known
    venue: str | None = None  # stadium (historical dataset)
    source: str = ""  # primary source file basename
    # Extended statistics (BR-Football-Dataset only, merged on dedupe)
    home_corners: int | None = None
    away_corners: int | None = None
    home_shots: int | None = None
    away_shots: int | None = None
    home_attacks: int | None = None
    away_attacks: int | None = None

    @property
    def played(self) -> bool:
        return self.home_goal is not None and self.away_goal is not None

    @property
    def score_text(self) -> str:
        if self.played:
            return f"{self.home_goal}-{self.away_goal}"
        return "vs"

    @property
    def total_goals(self) -> int | None:
        if self.played:
            return self.home_goal + self.away_goal
        return None

    @property
    def margin(self) -> int | None:
        """Absolute goal difference (used for biggest-wins ranking)."""
        if self.played:
            return abs(self.home_goal - self.away_goal)
        return None

    def involves(self, team: str) -> bool:
        return team in (self.home, self.away)

    def is_between(self, team_a: str, team_b: str) -> bool:
        return {self.home, self.away} == {team_a, team_b}

    def result_for(self, team: str) -> str | None:
        """"W", "D", "L" from ``team``'s perspective, or ``None``."""
        if not self.played or not self.involves(team):
            return None
        own, other = (
            (self.home_goal, self.away_goal) if team == self.home else (self.away_goal, self.home_goal)
        )
        if own > other:
            return "W"
        if own < other:
            return "L"
        return "D"

    def sort_key(self) -> tuple:
        return (self.date or date.min, self.competition, self.stage, self.home)


@dataclass(frozen=True)
class Player:
    """A FIFA-database player row (18,207 players, ~FIFA-19 era)."""

    fifa_id: int
    name: str
    age: int | None
    nationality: str
    overall: int
    potential: int
    club: str  # raw FIFA club spelling, e.g. "Atlético Mineiro"
    position: str  # FIFA position code, e.g. "LW", "GK"
    club_key: str | None = None  # canonical key when the club is a known team
    jersey: int | None = None
    height: str | None = None  # raw, e.g. "5'7"
    weight: str | None = None  # raw, e.g. "159lbs"
    value: str | None = None  # raw, e.g. "€110.5M"
    wage: str | None = None  # raw, e.g. "€565K"
    skill: dict = field(default_factory=dict)  # selected skill ratings

    def skill_text(self, *names: str) -> str:
        parts = [f"{n}: {self.skill[n]}" for n in names if n in self.skill]
        return ", ".join(parts)


@dataclass(frozen=True)
class TableRow:
    """One row of a computed league table (points-based ranking)."""

    position: int
    team: str  # canonical key
    display: str
    played: int
    win: int
    draw: int
    loss: int
    goals_for: int
    goals_against: int
    points: int

    @property
    def goal_diff(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def win_rate(self) -> float:
        return (self.win / self.played * 100.0) if self.played else 0.0


__all__ = ["Match", "Player", "TableRow"]
