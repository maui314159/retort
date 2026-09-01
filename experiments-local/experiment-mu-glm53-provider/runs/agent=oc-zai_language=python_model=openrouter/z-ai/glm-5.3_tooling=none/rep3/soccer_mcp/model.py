"""
soccer_mcp.model -- dataclasses shared across the Brazilian Soccer MCP server.

CONTEXT
-------
The MCP tools in ``soccer_mcp.tools`` answer natural-language questions about
Brazilian soccer by combining six Kaggle CSV datasets (see TASK.md).  This
module defines the in-memory representation of every entity the server works
with:

* ``Match`` / ``MatchStats`` -- one fixture, normalized across the five match
  files (dates, teams canonicalized, goals coerced to int);
* ``Player`` -- one FIFA-database row (18,207 players);
* ``TeamEntity`` / ``TeamResolution`` -- the team registry entry produced by
  the two-pass canonicalization in ``data_loader``;
* ``TeamRecord`` -- aggregated win/draw/loss/goal numbers for one team;
* ``StandingRow`` -- one row of a computed league table;
* ``FinalResult`` / ``KnockoutTie`` -- cup-final and knockout-bracket views;
* ``CompetitionCoverage`` -- seasons/sources/match counts per competition.

These structures are deliberately framework-free (plain dataclasses) so the
query layer can be tested without any MCP machinery.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class MatchStats:
    """Extended per-match statistics (only present for BR-Football rows)."""

    home_corners: int | None = None
    away_corners: int | None = None
    total_corners: int | None = None
    home_shots: int | None = None
    away_shots: int | None = None
    home_attacks: int | None = None
    away_attacks: int | None = None


@dataclass(frozen=True)
class Match:
    """One played fixture, normalized from any of the five match CSV files."""

    match_id: str
    competition: str  # competition id, e.g. "serie_a"
    source: str  # dataset id, e.g. "brasileirao_matches"
    season: str  # year as recorded ("2019")
    match_date: date | None  # None only if the row had an unusable date
    home_team: str  # canonical team id
    away_team: str  # canonical team id
    home_goals: int
    away_goals: int
    round_label: str | None = None  # "Round 22", "Final", "Group Stage", ...
    stage: str | None = None  # raw stage (Libertadores): "final", "group stage", ...
    stadium: str | None = None
    stats: MatchStats | None = None
    raw_home: str = ""
    raw_away: str = ""

    @property
    def is_home_win(self) -> bool:
        return self.home_goals > self.away_goals

    @property
    def is_away_win(self) -> bool:
        return self.home_goals < self.away_goals

    @property
    def is_draw(self) -> bool:
        return self.home_goals == self.away_goals

    @property
    def winner(self) -> str | None:
        """Canonical id of the winning team, or None for a draw."""
        if self.is_home_win:
            return self.home_team
        if self.is_away_win:
            return self.away_team
        return None

    @property
    def total_goals(self) -> int:
        return self.home_goals + self.away_goals

    @property
    def goal_margin(self) -> int:
        return abs(self.home_goals - self.away_goals)


#: Skill columns of the FIFA dataset exposed on ``Player.skills``.
SKILL_COLUMNS = (
    "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
    "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
    "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
    "ShotPower", "Jumping", "Stamina", "Strength", "LongShots", "Aggression",
    "Interceptions", "Positioning", "Vision", "Penalties", "Composure",
    "Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling",
    "GKKicking", "GKPositioning", "GKReflexes",
)


@dataclass(frozen=True)
class Player:
    """One row of the FIFA player database (fifa_data.csv)."""

    player_id: int
    name: str
    age: int | None
    nationality: str
    overall: int
    potential: int | None
    club: str  # raw FIFA club name ("" for free agents)
    position: str  # raw FIFA position code ("" when unknown)
    jersey_number: int | None
    height: str
    weight: str
    preferred_foot: str
    value: str
    wage: str
    skills: dict[str, int | None] = field(default_factory=dict)

    @property
    def position_group(self) -> str | None:
        from .normalize import position_group  # local import avoids a cycle

        return position_group(self.position)


@dataclass
class TeamEntity:
    """Registry entry for one club (or foreign side) seen anywhere in the data."""

    team_id: str  # canonical, e.g. "flamengo rj"
    base: str  # canonical base, e.g. "flamengo"
    state: str | None
    country: str | None
    display_name: str
    variants: dict[str, int] = field(default_factory=dict)  # raw spelling -> usage count
    sources: set[str] = field(default_factory=set)
    match_count: int = 0
    fifa_club_names: set[str] = field(default_factory=set)
    competitions: dict[str, set[str]] = field(default_factory=dict)  # comp id -> seasons

    @property
    def is_brazilian(self) -> bool:
        return self.country is None


@dataclass
class TeamResolution:
    """Result of resolving a user-supplied team name against the registry."""

    query: str
    team: TeamEntity | None
    alternatives: list[TeamEntity] = field(default_factory=list)
    error: str | None = None
    fuzzy: bool = False  # matched by substring rather than exactly

    @property
    def ok(self) -> bool:
        return self.team is not None


@dataclass
class TeamRecord:
    """Aggregated match record for one team (optionally home/away split)."""

    team_id: str
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
    def goal_diff(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def win_rate(self) -> float:
        return self.wins / self.matches if self.matches else 0.0

    def add_match(self, match: Match, team_id: str) -> None:
        home = match.home_team == team_id
        gf = match.home_goals if home else match.away_goals
        ga = match.away_goals if home else match.home_goals
        self.matches += 1
        self.goals_for += gf
        self.goals_against += ga
        if gf > ga:
            self.wins += 1
        elif gf == ga:
            self.draws += 1
        else:
            self.losses += 1


@dataclass
class StandingRow:
    """One row of a league table computed from match results."""

    position: int
    team_id: str
    matches: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    points: int

    @property
    def goal_diff(self) -> int:
        return self.goals_for - self.goals_against


@dataclass
class KnockoutTie:
    """A two-legged (or single-match) knockout pairing."""

    stage: str
    team_a: str
    team_b: str
    legs: list[Match] = field(default_factory=list)

    @property
    def agg_a(self) -> int:
        total = 0
        for leg in self.legs:
            if leg.home_team == self.team_a:
                total += leg.home_goals - leg.away_goals
            else:
                total += leg.away_goals - leg.home_goals
        return total

    @property
    def agg_b(self) -> int:
        return -self.agg_a

    @property
    def winner(self) -> str | None:
        if self.agg_a > 0:
            return self.team_a
        if self.agg_b > 0:
            return self.team_b
        return None


@dataclass
class FinalResult:
    """The final (or finals) of a cup competition in a given season."""

    competition: str
    season: str
    ties: list[KnockoutTie] = field(default_factory=list)
    note: str | None = None

    @property
    def winner(self) -> str | None:
        if len(self.ties) == 1:
            return self.ties[0].winner
        return None


@dataclass
class CompetitionCoverage:
    """What the loaded datasets contain for one competition."""

    competition: str
    display: str
    comp_type: str
    seasons: list[str] = field(default_factory=list)
    match_count: int = 0
    sources: dict[str, int] = field(default_factory=dict)  # source id -> matches
