"""Core dataclasses shared by loaders, the knowledge graph and the query engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

# Competition families (canonical keys used for cross-file matching/dedup)
SERIE_A = "serie_a"
SERIE_B = "serie_b"
SERIE_C = "serie_c"
COPA_DO_BRASIL = "copa_do_brasil"
LIBERTADORES = "libertadores"

FAMILY_DISPLAY = {
    SERIE_A: "Brasileirão Série A",
    SERIE_B: "Brasileirão Série B",
    SERIE_C: "Brasileirão Série C",
    COPA_DO_BRASIL: "Copa do Brasil",
    LIBERTADORES: "Copa Libertadores",
}


@dataclass(frozen=True)
class MatchStats:
    """Extended per-match statistics (only available for BR-Football rows)."""

    home_corners: int | None = None
    away_corners: int | None = None
    total_corners: int | None = None
    home_shots: int | None = None
    away_shots: int | None = None
    home_attacks: int | None = None
    away_attacks: int | None = None
    halftime_diff: int | None = None  # home goals minus away goals at halftime

    def as_dict(self) -> dict:
        return {
            "home_corners": self.home_corners,
            "away_corners": self.away_corners,
            "total_corners": self.total_corners,
            "home_shots": self.home_shots,
            "away_shots": self.away_shots,
            "home_attacks": self.home_attacks,
            "away_attacks": self.away_attacks,
            "halftime_diff": self.halftime_diff,
        }


@dataclass(frozen=True)
class Match:
    """A single football match, normalized across the six source files."""

    match_id: str
    date: date | None
    time: str | None
    family: str  # competition family key, e.g. "serie_a"
    season: int | None
    stage: str | None  # human stage descriptor ("Round 22", "final", ...)
    round: int | None
    home_team: str  # canonical club id
    away_team: str
    home_display: str
    away_display: str
    home_goals: int | None
    away_goals: int | None
    source: str
    stadium: str | None = None
    stats: MatchStats | None = None
    # non-primary sources describing the same fixture (filled during dedup)
    also_in_sources: tuple = field(default=())

    @property
    def competition(self) -> str:
        return FAMILY_DISPLAY.get(self.family, self.family)

    @property
    def played(self) -> bool:
        return self.home_goals is not None and self.away_goals is not None

    @property
    def total_goals(self) -> int | None:
        if self.played:
            return self.home_goals + self.away_goals
        return None

    @property
    def goal_margin(self) -> int | None:
        if self.played:
            return abs(self.home_goals - self.away_goals)
        return None

    def winner(self) -> str | None:
        """Return the club id of the winner, or None for a draw/unplayed match."""
        if not self.played:
            return None
        if self.home_goals > self.away_goals:
            return self.home_team
        if self.away_goals > self.home_goals:
            return self.away_team
        return None

    def result_for(self, club_id: str) -> str | None:
        """"W", "D", "L" from the perspective of club_id, or None if not involved."""
        if club_id == self.home_team:
            if not self.played:
                return None
            if self.home_goals > self.away_goals:
                return "W"
            if self.home_goals < self.away_goals:
                return "L"
            return "D"
        if club_id == self.away_team:
            if not self.played:
                return None
            if self.away_goals > self.home_goals:
                return "W"
            if self.away_goals < self.home_goals:
                return "L"
            return "D"
        return None

    def as_dict(self) -> dict:
        d = {
            "match_id": self.match_id,
            "date": self.date.isoformat() if self.date else None,
            "time": self.time,
            "competition": self.competition,
            "season": self.season,
            "stage": self.stage,
            "round": self.round,
            "home_team": self.home_display,
            "away_team": self.away_display,
            "home_team_id": self.home_team,
            "away_team_id": self.away_team,
            "score": (
                f"{self.home_goals}-{self.away_goals}" if self.played else "not recorded"
            ),
            "goal_margin": self.goal_margin,
            "winner": self.winner(),
            "source": self.source,
        }
        if self.stadium:
            d["stadium"] = self.stadium
        if self.stats:
            d["stats"] = self.stats.as_dict()
        if self.also_in_sources:
            d["also_in_sources"] = list(self.also_in_sources)
        return d


@dataclass(frozen=True)
class Player:
    """A player from the FIFA dataset (FIFA 19 snapshot)."""

    fifa_id: int
    name: str
    age: int | None
    nationality: str
    overall: int
    potential: int
    club: str | None  # raw FIFA club name (may be None for free agents)
    club_id: str | None  # canonical club id when the club is in the registry
    position: str | None
    jersey: int | None
    value_eur: int | None
    wage_eur: int | None
    preferred_foot: str | None

    def as_dict(self) -> dict:
        return {
            "fifa_id": self.fifa_id,
            "name": self.name,
            "age": self.age,
            "nationality": self.nationality,
            "overall": self.overall,
            "potential": self.potential,
            "club": self.club or "Free agent",
            "position": self.position,
            "jersey_number": self.jersey,
            "value_eur": self.value_eur,
            "wage_eur": self.wage_eur,
            "preferred_foot": self.preferred_foot,
        }


@dataclass
class TeamRecord:
    """Aggregated win/draw/loss record for one team."""

    club_id: str
    display: str
    matches: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0

    @property
    def points(self) -> int:
        return 3 * self.wins + self.draws

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def win_rate(self) -> float:
        return self.wins / self.matches if self.matches else 0.0

    def add(self, result: str, goals_for: int, goals_against: int) -> None:
        self.matches += 1
        self.goals_for += goals_for
        self.goals_against += goals_against
        if result == "W":
            self.wins += 1
        elif result == "D":
            self.draws += 1
        else:
            self.losses += 1

    def as_dict(self) -> dict:
        return {
            "team": self.display,
            "team_id": self.club_id,
            "matches": self.matches,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses,
            "goals_for": self.goals_for,
            "goals_against": self.goals_against,
            "goal_difference": self.goal_difference,
            "points": self.points,
            "win_rate": round(self.win_rate * 100, 1),
        }
