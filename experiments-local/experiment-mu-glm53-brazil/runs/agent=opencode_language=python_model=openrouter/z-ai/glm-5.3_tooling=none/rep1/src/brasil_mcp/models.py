"""Core data models for matches and players."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Match:
    """A single soccer match from any of the provided datasets."""

    source: str
    competition: str
    home: str
    away: str
    home_display: str
    away_display: str
    date: date | None = None
    time: str | None = None
    season: int | None = None
    round: str | None = None
    stage: str | None = None
    home_goals: int | None = None
    away_goals: int | None = None
    venue: str | None = None
    home_state: str | None = None
    away_state: str | None = None
    home_corners: int | None = None
    away_corners: int | None = None
    total_corners: int | None = None
    home_shots: int | None = None
    away_shots: int | None = None
    home_attacks: int | None = None
    away_attacks: int | None = None
    ht_result: str | None = None
    at_result: str | None = None

    @property
    def played(self) -> bool:
        return self.home_goals is not None and self.away_goals is not None

    @property
    def score_str(self) -> str:
        if self.played:
            return f"{self.home_goals}-{self.away_goals}"
        return "vs"

    @property
    def goals(self) -> int | None:
        if self.played:
            return self.home_goals + self.away_goals
        return None

    @property
    def margin(self) -> int | None:
        if self.played:
            return abs(self.home_goals - self.away_goals)
        return None

    def involves(self, team: str) -> bool:
        return team in (self.home, self.away)

    def opponent_of(self, team: str) -> str:
        return self.away if team == self.home else self.home

    def result_for(self, team: str) -> str | None:
        """Return 'W', 'D' or 'L' from the perspective of ``team``."""
        if not self.played:
            return None
        if self.home_goals == self.away_goals:
            return "D"
        home_won = self.home_goals > self.away_goals
        if team == self.home:
            return "W" if home_won else "L"
        return "L" if home_won else "W"

    def goals_for(self, team: str) -> int | None:
        if not self.played:
            return None
        if team == self.home:
            return self.home_goals
        return self.away_goals

    def goals_against(self, team: str) -> int | None:
        if not self.played:
            return None
        if team == self.home:
            return self.away_goals
        return self.home_goals

    def stage_label(self) -> str:
        parts: list[str] = []
        if self.stage:
            parts.append(self.stage)
        elif self.round:
            parts.append(f"Round {self.round}")
        return " ".join(parts)

    def label(self) -> str:
        date_str = self.date.isoformat() if self.date else "date unknown"
        stage = self.stage_label()
        suffix = f" ({self.competition}{' ' + stage if stage else ''})"
        return f"{date_str}: {self.home_display} {self.score_str} {self.away_display}{suffix}"

    def to_dict(self) -> dict:
        return {
            "date": self.date.isoformat() if self.date else None,
            "time": self.time,
            "home_team": self.home_display,
            "away_team": self.away_display,
            "home_goals": self.home_goals,
            "away_goals": self.away_goals,
            "competition": self.competition,
            "season": self.season,
            "round": self.round,
            "stage": self.stage,
            "venue": self.venue,
            "source": self.source,
            "stats": {
                "corners": [self.home_corners, self.away_corners],
                "shots": [self.home_shots, self.away_shots],
                "attacks": [self.home_attacks, self.away_attacks],
                "half_time": [self.ht_result, self.at_result],
            },
        }


@dataclass
class TeamRecord:
    """Aggregated win/draw/loss record for one team."""

    team: str
    display: str
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
    def goal_diff(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def win_rate(self) -> float:
        return self.wins / self.matches if self.matches else 0.0

    def add(self, match: Match) -> None:
        if not match.involves(self.team) or not match.played:
            return
        self.matches += 1
        result = match.result_for(self.team)
        if result == "W":
            self.wins += 1
        elif result == "D":
            self.draws += 1
        else:
            self.losses += 1
        self.goals_for += match.goals_for(self.team) or 0
        self.goals_against += match.goals_against(self.team) or 0

    def to_dict(self) -> dict:
        return {
            "team": self.display,
            "matches": self.matches,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses,
            "goals_for": self.goals_for,
            "goals_against": self.goals_against,
            "goal_diff": self.goal_diff,
            "points": self.points,
            "win_rate": round(self.win_rate * 100, 1),
        }


@dataclass
class Player:
    """A player from the FIFA dataset."""

    id: int
    name: str
    age: int | None
    nationality: str
    overall: int | None
    potential: int | None
    club: str
    position: str
    jersey: int | None
    height: str | None
    weight: str | None
    preferred_foot: str | None
    value: str | None
    wage: str | None
    skills: dict[str, int | None] = field(default_factory=dict)

    def to_dict(self) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "age": self.age,
            "nationality": self.nationality,
            "overall": self.overall,
            "potential": self.potential,
            "club": self.club,
            "position": self.position,
            "jersey": self.jersey,
            "height": self.height,
            "weight": self.weight,
            "preferred_foot": self.preferred_foot,
            "value": self.value,
            "wage": self.wage,
        }
        data.update(self.skills)
        return data
