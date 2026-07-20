"""Dataclass models for the Brazilian Soccer knowledge graph.

Context
-------
The MCP server answers questions about matches, teams, players and
competitions.  To keep the query layer (and the LLM-facing tool output)
independent of the on-disk CSV layout, every row from every source file is
projected into one of the plain dataclasses defined here:

* :class:`MatchRecord` — a single game, regardless of which file it came
  from, with a uniform ``competition`` label and an ISO ``date``.
* :class:`PlayerRecord` — a single FIFA player row, trimmed to the columns
  the spec calls out (identity, ratings, club, position, physical attrs).

These dataclasses are intentionally framework-free (no pandas, no MCP) so
they can be exercised directly from unit tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Any, Optional


@dataclass(frozen=True)
class MatchRecord:
    """A normalized match drawn from any of the five match CSV files."""

    date: Optional[date]
    season: Optional[int]
    competition: str
    home_team: str
    away_team: str
    home_goal: Optional[int]
    away_goal: Optional[int]
    round: Optional[str] = None
    stage: Optional[str] = None
    home_state: Optional[str] = None
    away_state: Optional[str] = None
    venue: Optional[str] = None
    # Extended statistics only present for BR-Football-Dataset rows.
    home_corners: Optional[float] = None
    away_corners: Optional[float] = None
    home_shots: Optional[float] = None
    away_shots: Optional[float] = None
    home_attacks: Optional[float] = None
    away_attacks: Optional[float] = None
    total_corners: Optional[float] = None
    # Provenance: which source file produced this row.
    source: str = ""

    @property
    def total_goals(self) -> Optional[int]:
        if self.home_goal is None or self.away_goal is None:
            return None
        return self.home_goal + self.away_goal

    def result_for(self, team: str) -> Optional[str]:
        """Return "win"/"loss"/"draw" for *team*.

        *team* should be the **canonical** display name (the same spelling
        stored on :attr:`home_team` / :attr:`away_team`, produced by the
        :class:`~brazilian_soccer_mcp.normalize.TeamNameNormalizer` during
        loading).  Callers that hold a raw user spelling should canonicalize
        it first.
        """

        if self.home_goal is None or self.away_goal is None:
            return None
        if team == self.home_team:
            if self.home_goal > self.away_goal:
                return "win"
            if self.home_goal < self.away_goal:
                return "loss"
            return "draw"
        if team == self.away_team:
            if self.away_goal > self.home_goal:
                return "win"
            if self.away_goal < self.home_goal:
                return "loss"
            return "draw"
        return None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["date"] = self.date.isoformat() if self.date else None
        return d


@dataclass(frozen=True)
class PlayerRecord:
    """A normalized FIFA player row."""

    id: int
    name: str
    age: Optional[int]
    nationality: str
    overall: int
    potential: int
    club: str
    position: str
    jersey_number: Optional[int] = None
    height: Optional[str] = None
    weight: Optional[str] = None
    preferred_foot: Optional[str] = None
    # A handful of representative skill ratings surfaced for ranking.
    crossing: Optional[int] = None
    finishing: Optional[int] = None
    dribbling: Optional[int] = None
    short_passing: Optional[int] = None
    long_shots: Optional[int] = None
    sprint_speed: Optional[int] = None
    standing_tackle: Optional[int] = None
    gk_reflexes: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
