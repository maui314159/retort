"""Data models for matches and players."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date


@dataclass
class Match:
    """A single soccer match from any of the source datasets."""

    date: date | None
    home: str
    away: str
    home_key: str
    away_key: str
    home_goals: int | None
    away_goals: int | None
    competition: str
    competition_key: str
    season: int | None
    source: str
    round_label: str | None = None
    stage: str | None = None
    venue: str | None = None
    time: str | None = None
    home_corners: int | None = None
    away_corners: int | None = None
    home_shots: int | None = None
    away_shots: int | None = None
    home_attacks: int | None = None
    away_attacks: int | None = None
    halftime_result: str | None = None

    @property
    def has_result(self) -> bool:
        return self.home_goals is not None and self.away_goals is not None

    @property
    def total_goals(self) -> int | None:
        if not self.has_result:
            return None
        return self.home_goals + self.away_goals

    def goal_margin(self) -> int:
        return abs(self.home_goals - self.away_goals)

    def winner_key(self) -> str | None:
        """Canonical key of the winning team, or None for a draw."""
        if not self.has_result:
            return None
        if self.home_goals > self.away_goals:
            return self.home_key
        if self.away_goals > self.home_goals:
            return self.away_key
        return None

    def involves(self, team_key: str) -> bool:
        return team_key in (self.home_key, self.away_key)

    def involves_pair(self, key_a: str, key_b: str) -> bool:
        return {self.home_key, self.away_key} == {key_a, key_b}

    def score_display(self) -> str:
        home = "?" if self.home_goals is None else self.home_goals
        away = "?" if self.away_goals is None else self.away_goals
        return f"{home}-{away}"

    def summary(self) -> str:
        date_text = self.date.isoformat() if self.date else "unknown date"
        parts = [f"{date_text}: {self.home} {self.score_display()} {self.away}"]
        context = self.competition
        if self.round_label:
            context += f", {self.round_label}"
        if self.stage:
            context += f", {self.stage}"
        parts.append(f"({context})")
        return " ".join(parts)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["date"] = self.date.isoformat() if self.date else None
        data["score"] = self.score_display()
        return data


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
    club_key: str
    position: str
    jersey_number: int | None
    height: str
    weight: str
    preferred_foot: str
    value: str
    wage: str

    def to_dict(self) -> dict:
        return asdict(self)


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
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def win_rate(self) -> float:
        return round(self.wins / self.matches, 3) if self.matches else 0.0

    def add_match(self, team_key: str, match: Match) -> None:
        self.matches += 1
        gf = match.home_goals if team_key == match.home_key else match.away_goals
        ga = match.away_goals if team_key == match.home_key else match.home_goals
        self.goals_for += gf
        self.goals_against += ga
        if gf > ga:
            self.wins += 1
        elif gf == ga:
            self.draws += 1
        else:
            self.losses += 1

    def to_dict(self) -> dict:
        return {
            "team": self.team,
            "display": self.display,
            "matches": self.matches,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses,
            "goals_for": self.goals_for,
            "goals_against": self.goals_against,
            "goal_difference": self.goal_difference,
            "points": self.points,
            "win_rate": self.win_rate,
        }
