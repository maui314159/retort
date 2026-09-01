"""Data models for the Brazilian soccer knowledge base.

CONTEXT
-------
Plain dataclasses shared by loaders, analytics and the query service.
``Match`` is the unified representation of one fixture from any of the
five match CSV files (deduplicated across files); ``Player`` is one row
of the FIFA dataset.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class MatchStats:
    """Optional per-match statistics (only available from BR-Football-Dataset.csv)."""

    home_corners: int | None = None
    away_corners: int | None = None
    home_shots: int | None = None
    away_shots: int | None = None
    home_attacks: int | None = None
    away_attacks: int | None = None

    @property
    def is_empty(self) -> bool:
        return all(
            v is None
            for v in (
                self.home_corners,
                self.away_corners,
                self.home_shots,
                self.away_shots,
                self.home_attacks,
                self.away_attacks,
            )
        )


@dataclass
class Match:
    """One fixture, normalized across data sources.

    ``home``/``away`` are entity keys of the form ``"base|REGION"``.
    ``home_goals``/``away_goals`` are ``None`` when the dataset records the
    fixture without a score (e.g. unplayed/postponed matches).
    """

    competition: str
    season: int | None
    date: date | None
    home: str
    away: str
    home_goals: int | None
    away_goals: int | None
    round_label: str | None = None  # "Round 22", "Semifinal", "Final", ...
    stage: str | None = None  # raw stage (Libertadores)
    venue: str | None = None  # stadium (novo dataset)
    kickoff: str | None = None  # "18:30"
    halftime: str | None = None  # home perspective: "WON"/"DRAW"/"LOST"
    stats: MatchStats | None = None
    sources: list[str] = field(default_factory=list)

    @property
    def has_score(self) -> bool:
        return self.home_goals is not None and self.away_goals is not None

    @property
    def margin(self) -> int | None:
        if not self.has_score:
            return None
        return abs(self.home_goals - self.away_goals)  # type: ignore[operator]

    def winner(self) -> str | None:
        """Entity key of the winner, or None for a draw / unknown score."""
        if not self.has_score:
            return None
        if self.home_goals > self.away_goals:  # type: ignore[operator]
            return self.home
        if self.away_goals > self.home_goals:  # type: ignore[operator]
            return self.away
        return None

    def score_str(self) -> str:
        if self.has_score:
            return f"{self.home_goals}-{self.away_goals}"
        return "score unknown"


#: Position group derived from the FIFA position code.
POSITION_GROUPS: dict[str, str] = {}
for _code, _group in [
    *[(c, "GK") for c in ["GK"]],
    *[(c, "DEF") for c in ["CB", "LCB", "RCB", "LB", "RB", "LWB", "RWB"]],
    *[(c, "MID") for c in ["CDM", "LDM", "RDM", "CM", "LCM", "RCM", "CAM", "LAM", "RAM", "LM", "RM"]],
    *[(c, "FWD") for c in ["ST", "CF", "LS", "RS", "LW", "RW", "LF", "RF"]],
]:
    POSITION_GROUPS[_code] = _group


def position_group(position: str | None) -> str | None:
    if not position:
        return None
    return POSITION_GROUPS.get(position.strip().upper())


@dataclass
class Player:
    """One FIFA-dataset player row."""

    id: str
    name: str
    age: int | None
    nationality: str
    overall: int | None
    potential: int | None
    club: str
    position: str | None
    jersey: int | None
    height: str | None
    weight: str | None
    foot: str | None
    value: str | None
    wage: str | None
    skills: dict[str, int] = field(default_factory=dict)

    @property
    def position_group(self) -> str | None:
        return position_group(self.position)
