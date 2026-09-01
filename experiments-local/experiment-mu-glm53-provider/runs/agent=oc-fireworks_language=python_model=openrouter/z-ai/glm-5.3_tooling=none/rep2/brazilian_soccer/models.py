"""Data model entities for the Brazilian soccer knowledge graph."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TeamRef:
    """Reference to a team inside a match (key + pretty display name)."""

    key: str
    display: str


@dataclass
class MatchStats:
    """Extended per-match statistics from the BR-Football dataset."""

    home_corners: int | None = None
    away_corners: int | None = None
    home_shots: int | None = None
    away_shots: int | None = None
    home_attacks: int | None = None
    away_attacks: int | None = None

    def describe(self) -> str:
        parts = []
        if self.home_corners is not None and self.away_corners is not None:
            parts.append(f"corners {self.home_corners}-{self.away_corners}")
        if self.home_shots is not None and self.away_shots is not None:
            parts.append(f"shots {self.home_shots}-{self.away_shots}")
        if self.home_attacks is not None and self.away_attacks is not None:
            parts.append(f"attacks {self.home_attacks}-{self.away_attacks}")
        return ", ".join(parts)


@dataclass
class Match:
    """A single match, merged from one or more source files."""

    competition: str              # canonical competition id
    competition_display: str      # e.g. "Brasileirão Serie A"
    season: int | None
    date: date | None
    time: str | None
    home: TeamRef
    away: TeamRef
    home_goals: int | None = None      # None => not played / not recorded
    away_goals: int | None = None
    stage: str | None = None           # "final", "semifinals", ... (cups)
    round_label: str | None = None     # "Round 22", "Final", ...
    venue: str | None = None           # stadium (historical file only)
    stats: MatchStats | None = None
    source: str = ""

    @property
    def played(self) -> bool:
        return self.home_goals is not None and self.away_goals is not None

    @property
    def total_goals(self) -> int:
        return (self.home_goals or 0) + (self.away_goals or 0)

    @property
    def margin(self) -> int:
        return abs((self.home_goals or 0) - (self.away_goals or 0))

    def result_for(self, team_key: str) -> str | None:
        """Return "W", "D" or "L" from the perspective of team_key."""
        if not self.played:
            return None
        if self.home.key == team_key:
            own, other = self.home_goals, self.away_goals
        elif self.away.key == team_key:
            own, other = self.away_goals, self.home_goals
        else:
            return None
        if own > other:
            return "W"
        if own < other:
            return "L"
        return "D"

    def describe(self, include_stats: bool = True) -> str:
        """One-line human description, e.g.

        "2019-09-03: Flamengo 2-1 Fluminense (Brasileirão Round 22)"
        """
        when = self.date.isoformat() if self.date else "date unknown"
        if self.played:
            score = f"{self.home.display} {self.home_goals}-{self.away_goals} {self.away.display}"
        else:
            score = f"{self.home.display} vs {self.away.display} (not played/recorded)"
        context = self.competition_display
        label = self.stage_label()
        if label:
            context += f" {label}"
        line = f"{when}: {score} ({context})"
        if include_stats and self.stats:
            extra = self.stats.describe()
            if extra:
                line += f" [{extra}]"
        return line

    def stage_label(self) -> str:
        return self.stage or self.round_label or ""


@dataclass
class Player:
    """A player from the FIFA dataset."""

    player_id: int
    name: str
    age: int | None
    nationality: str
    overall: int
    potential: int
    club: str | None          # None => free agent / no club
    position: str | None      # FIFA position code, e.g. "ST"
    jersey: int | None
    preferred_foot: str | None
    value: str | None
    wage: str | None
    height: str | None
    weight: str | None

    def position_group(self) -> str:
        return POSITION_GROUPS.get(self.position or "", "Unknown")


# FIFA position codes grouped into roles.
POSITION_GROUPS: dict[str, str] = {}
for code in ("GK",):
    POSITION_GROUPS[code] = "Goalkeeper"
for code in ("CB", "LCB", "RCB", "LB", "RB", "LWB", "RWB"):
    POSITION_GROUPS[code] = "Defender"
for code in ("CDM", "LDM", "RDM", "CM", "LCM", "RCM", "CAM", "LAM", "RAM", "LM", "RM"):
    POSITION_GROUPS[code] = "Midfielder"
for code in ("ST", "LS", "RS", "LW", "RW", "LF", "RF", "CF"):
    POSITION_GROUPS[code] = "Forward"


@dataclass
class TeamRecord:
    """Aggregated win/draw/loss record for a team."""

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

    def describe(self) -> str:
        rate = f"{self.win_rate:.1%}"
        return (
            f"Matches: {self.matches}, Wins: {self.wins}, Draws: {self.draws}, "
            f"Losses: {self.losses}, Goals For: {self.goals_for}, "
            f"Goals Against: {self.goals_against}, Win rate: {rate}"
        )
