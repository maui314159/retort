from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Optional


@dataclass
class Match:
    date: Optional[date]
    home_id: str
    home_name: str
    away_id: str
    away_name: str
    home_goal: int
    away_goal: int
    season: Optional[int]
    competition: str
    round: Optional[int] = None
    stage: Optional[str] = None
    stadium: Optional[str] = None
    home_state: Optional[str] = None
    away_state: Optional[str] = None
    sources: list = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["date"] = self.date.isoformat() if self.date else None
        return d

    @property
    def goal_diff(self) -> int:
        return abs(self.home_goal - self.away_goal)

    @property
    def result(self) -> str:
        if self.home_goal > self.away_goal:
            return "home_win"
        if self.away_goal > self.home_goal:
            return "away_win"
        return "draw"


@dataclass
class TeamStats:
    team_id: str
    team_name: str
    season: Optional[int]
    competition: Optional[str]
    home_away: str
    matches: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    win_rate: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class StandingRow:
    position: int
    team_id: str
    team_name: str
    matches: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class HeadToHead:
    team_a_id: str
    team_a_name: str
    team_b_id: str
    team_b_name: str
    team_a_wins: int
    team_b_wins: int
    draws: int
    team_a_goals: int
    team_b_goals: int
    matches: list

    def to_dict(self) -> dict:
        d = asdict(self)
        d["matches"] = [m.to_dict() if hasattr(m, "to_dict") else m for m in self.matches]
        return d


@dataclass
class Player:
    id: int
    name: str
    age: Optional[int]
    nationality: str
    overall: int
    potential: int
    club_id: str
    club: str
    position: Optional[str]
    jersey_number: Optional[int]
    height: Optional[str]
    weight: Optional[str]
    preferred_foot: Optional[str] = None
    skills: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CompetitionStat:
    label: str
    value: float

    def to_dict(self) -> dict:
        return asdict(self)
