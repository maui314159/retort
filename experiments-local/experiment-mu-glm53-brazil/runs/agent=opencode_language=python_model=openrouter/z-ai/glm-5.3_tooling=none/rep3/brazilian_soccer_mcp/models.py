"""
Domain models for the Brazilian Soccer MCP server.

Context block
-------------
Why:
    The service layer needs stable, typed records to query and serialize.
    Raw CSV rows are re-shaped exactly once (in ``dataset.py``) into the
    dataclasses below; every tool then works with these models only.

What:
    * ``Match``        - one match from any source, with normalized team ids.
    * ``MatchStats``   - extended per-match statistics (BR-Football only:
                         corners, shots, attacks, half-time results).
    * ``Player``       - one FIFA-database player row.
    * ``StandingRow``  - one row of a computed league table.
    * ``Club``         - one club entity in the knowledge graph.

Test:
    Covered indirectly by every query test; construction invariants (e.g.
    ``Match.score``) are asserted in ``tests/test_dataset.py``.

Spec references:
    TASK.md "Provided Data" (column meanings for all six CSV files) and
    "Example answer format" sections that define the derived fields
    (winner, score string, points).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as Date

from .normalize import TeamName


@dataclass
class MatchStats:
    """Extended statistics attached to matches from BR-Football-Dataset.csv."""

    home_corners: int | None = None
    away_corners: int | None = None
    home_shots: int | None = None
    away_shots: int | None = None
    home_attacks: int | None = None
    away_attacks: int | None = None
    home_ht_result: str | None = None  # 'WON' / 'LOST' / 'DRAW' (home view)
    away_ht_result: str | None = None
    kickoff_time: str | None = None

    def to_dict(self) -> dict:
        return {
            "kickoff_time": self.kickoff_time,
            "corners": f"{self.home_corners}-{self.away_corners}"
            if self.home_corners is not None and self.away_corners is not None
            else None,
            "shots": f"{self.home_shots}-{self.away_shots}"
            if self.home_shots is not None and self.away_shots is not None
            else None,
            "attacks": f"{self.home_attacks}-{self.away_attacks}"
            if self.home_attacks is not None and self.away_attacks is not None
            else None,
            "half_time": self.home_ht_result,
        }


@dataclass
class Match:
    """A single soccer match from any of the five match datasets."""

    date: Date | None
    home_name: str  # raw display name from the source
    away_name: str
    home_team: TeamName  # normalized identity
    away_team: TeamName
    home_goals: int | None
    away_goals: int | None
    competition: str  # canonical competition name
    season: int | None
    round: str | None = None  # league round / cup round label
    stage: str | None = None  # Libertadores stage label
    source: str = ""  # originating CSV file stem
    stadium: str | None = None  # novo dataset only
    stats: MatchStats | None = None  # BR-Football extended stats
    _home_club: str | None = field(default=None, repr=False)
    _away_club: str | None = field(default=None, repr=False)

    @property
    def has_score(self) -> bool:
        return self.home_goals is not None and self.away_goals is not None

    @property
    def score(self) -> str:
        if self.has_score:
            return f"{self.home_goals}-{self.away_goals}"
        return "N/A"

    @property
    def winner(self) -> str | None:
        """'home', 'away', 'draw' or None when the score is unknown."""
        if not self.has_score:
            return None
        if self.home_goals > self.away_goals:
            return "home"
        if self.home_goals < self.away_goals:
            return "away"
        return "draw"

    @property
    def margin(self) -> int | None:
        if not self.has_score:
            return None
        return abs(self.home_goals - self.away_goals)

    def to_dict(self) -> dict:
        data = {
            "date": self.date.isoformat() if self.date else None,
            "home_team": self.home_name,
            "away_team": self.away_name,
            "score": self.score,
            "home_goals": self.home_goals,
            "away_goals": self.away_goals,
            "competition": self.competition,
            "season": self.season,
            "round": self.round,
            "stage": self.stage,
            "stadium": self.stadium,
            "source": self.source,
            "winner": self.winner,
        }
        if self.stats is not None:
            data["statistics"] = self.stats.to_dict()
        return data


@dataclass
class Player:
    """One player row from the FIFA dataset (fifa_data.csv)."""

    player_id: int
    name: str
    age: int | None
    nationality: str
    overall: int
    potential: int
    club: str
    position: str | None
    jersey_number: int | None
    preferred_foot: str | None
    value: str | None
    wage: str | None
    height: str | None
    weight: str | None
    skills: dict[str, int] = field(default_factory=dict)
    _club_team: TeamName | None = field(default=None, repr=False)
    _club_id: str | None = field(default=None, repr=False)  # merged club id

    def to_dict(self) -> dict:
        return {
            "id": self.player_id,
            "name": self.name,
            "age": self.age,
            "nationality": self.nationality,
            "overall": self.overall,
            "potential": self.potential,
            "club": self.club,
            "position": self.position,
            "jersey_number": self.jersey_number,
            "preferred_foot": self.preferred_foot,
            "value": self.value,
            "wage": self.wage,
            "height": self.height,
            "weight": self.weight,
            "skills": self.skills or None,
        }


@dataclass
class StandingRow:
    """One row of a league table computed from match results."""

    rank: int
    team: str
    matches: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_diff: int
    points: int
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "rank": self.rank,
            "team": self.team,
            "matches": self.matches,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses,
            "goals_for": self.goals_for,
            "goals_against": self.goals_against,
            "goal_diff": self.goal_diff,
            "points": self.points,
            "notes": self.notes or None,
        }


@dataclass
class Club:
    """A club node in the knowledge graph.

    A club groups every spelling variant seen across the datasets (plus the
    FIFA club string when one resolves to this club).  ``match_count`` is
    the number of match appearances and ``player_count`` the number of FIFA
    players at the club; together they drive disambiguation ranking.
    """

    id: str  # canonical key "base|state" or "base|"
    base: str
    state: str | None
    variant_counts: dict[str, int] = field(default_factory=dict)  # raw spelling -> times seen
    match_count: int = 0
    player_count: int = 0
    merged_into: str | None = None  # set when absorbed by another club

    @property
    def variants(self) -> list[str]:
        return [v for v, _ in sorted(self.variant_counts.items(), key=lambda kv: (-kv[1], kv[0]))]

    @property
    def display(self) -> str:
        from .normalize import canonical_display_name

        # Prefer a curated name; else use the most frequently seen spelling.
        curated = canonical_display_name(self.id, "")
        if curated:
            return curated
        ordered = self.variants
        return ordered[0] if ordered else self.base
