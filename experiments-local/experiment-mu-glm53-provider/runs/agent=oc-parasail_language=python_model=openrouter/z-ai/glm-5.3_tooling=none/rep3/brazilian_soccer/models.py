"""Dataclasses shared across the Brazilian soccer MCP server.

The loader converts every CSV row into one of these models; the analysis
layer computes derived records (``TeamRecord``, ``StandingRow``) from them
and the MCP server renders them as text.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

__all__ = [
    "MatchStats",
    "Match",
    "Player",
    "TeamRecord",
    "StandingRow",
    "CompetitionInfo",
    "CompetitionStandings",
]


@dataclass(frozen=True)
class MatchStats:
    """Extended per-match statistics (from BR-Football-Dataset.csv)."""

    corners_home: Optional[int] = None
    corners_away: Optional[int] = None
    shots_home: Optional[int] = None
    shots_away: Optional[int] = None
    attacks_home: Optional[int] = None
    attacks_away: Optional[int] = None
    ht_result_home: Optional[str] = None  # WON / LOST / DRAW
    ht_result_away: Optional[str] = None


@dataclass
class Match:
    """A single played match, normalized across all source files."""

    match_id: str
    competition_id: str
    competition: str
    season: Optional[int]
    date: Optional[date]
    home_key: str
    home_team: str
    away_key: str
    away_team: str
    home_goals: int
    away_goals: int
    stage: str = ""
    round_number: Optional[int] = None
    kickoff: Optional[str] = None
    stadium: Optional[str] = None
    state_home: Optional[str] = None
    state_away: Optional[str] = None
    stats: Optional[MatchStats] = None
    source: str = ""

    @property
    def winner(self) -> Optional[str]:
        """'home', 'away' or 'draw'."""
        if self.home_goals > self.away_goals:
            return "home"
        if self.away_goals > self.home_goals:
            return "away"
        return "draw"

    @property
    def winner_key(self) -> Optional[str]:
        w = self.winner
        if w == "home":
            return self.home_key
        if w == "away":
            return self.away_key
        return None

    @property
    def margin(self) -> int:
        return abs(self.home_goals - self.away_goals)

    @property
    def score(self) -> str:
        return f"{self.home_team} {self.home_goals}-{self.away_goals} {self.away_team}"

    def involves(self, team_key_: str) -> bool:
        return team_key_ in (self.home_key, self.away_key)

    def opponent_of(self, team_key_: str) -> tuple[str, int, int]:
        """Return (opponent display, goals for, goals against) for one side."""
        if team_key_ == self.home_key:
            return self.away_team, self.home_goals, self.away_goals
        return self.home_team, self.away_goals, self.home_goals


@dataclass(frozen=True)
class Player:
    """A FIFA-database player."""

    player_id: str
    name: str
    age: Optional[int]
    nationality: str
    overall: Optional[int]
    potential: Optional[int]
    club: str
    club_key: str
    position: str
    position_group: str
    jersey: Optional[int]
    height: Optional[str]
    weight: Optional[str]
    preferred_foot: Optional[str]
    value: Optional[str]
    wage: Optional[str]
    skills: dict = field(default_factory=dict)


FORWARD_POSITIONS = {"ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"}
MIDFIELD_POSITIONS = {"CAM", "CM", "CDM", "LM", "RM", "LAM", "RAM", "LCM", "RCM", "LDM", "RDM"}
DEFENDER_POSITIONS = {"LB", "RB", "CB", "LCB", "RCB", "LWB", "RWB"}


def position_group(position: str) -> str:
    p = (position or "").upper()
    if p in FORWARD_POSITIONS:
        return "Forward"
    if p in MIDFIELD_POSITIONS:
        return "Midfielder"
    if p in DEFENDER_POSITIONS:
        return "Defender"
    if p == "GK":
        return "Goalkeeper"
    return "Unknown"


@dataclass
class TeamRecord:
    """Aggregated win/draw/loss record for a team (optionally filtered)."""

    team_key: str = ""
    team: str = ""
    matches: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0

    def add_match(self, match: Match, team_key_: str) -> None:
        if not self.team:
            self.team_key = team_key_
            info = match.home_team if match.home_key == team_key_ else match.away_team
            self.team = info
        gf, ga = match.opponent_of(team_key_)[1], match.opponent_of(team_key_)[2]
        self.matches += 1
        self.goals_for += gf
        self.goals_against += ga
        result = "home" if match.home_key == team_key_ else "away"
        winner = match.winner
        if winner == "draw":
            self.draws += 1
        elif winner == result:
            self.wins += 1
        else:
            self.losses += 1

    @property
    def points(self) -> int:
        return self.wins * 3 + self.draws

    @property
    def goal_diff(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def win_rate(self) -> float:
        return self.wins / self.matches if self.matches else 0.0

    @property
    def points_rate(self) -> float:
        return self.points / (self.matches * 3) if self.matches else 0.0

    def summary_line(self) -> str:
        rate = f"{self.win_rate * 100:.1f}%"
        return (
            f"Matches: {self.matches}, Wins: {self.wins}, Draws: {self.draws}, "
            f"Losses: {self.losses}, Goals For: {self.goals_for}, "
            f"Goals Against: {self.goals_against}, Win rate: {rate}"
        )


@dataclass(frozen=True)
class StandingRow:
    position: int
    team_key: str
    team: str
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_diff: int
    points: int


@dataclass
class CompetitionInfo:
    competition_id: str
    display: str
    kind: str  # "league" or "cup"
    seasons: list[int] = field(default_factory=list)
    match_count: int = 0
    team_count: int = 0
    sources: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class CompetitionStandings:
    competition_id: str
    competition: str
    season: int
    rows: list[StandingRow] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def champion(self) -> Optional[StandingRow]:
        return self.rows[0] if self.rows else None

    @property
    def relegated(self) -> list[StandingRow]:
        """Bottom four of the table (typical Brasileirão relegation zone)."""
        return self.rows[-4:] if len(self.rows) >= 4 else []
