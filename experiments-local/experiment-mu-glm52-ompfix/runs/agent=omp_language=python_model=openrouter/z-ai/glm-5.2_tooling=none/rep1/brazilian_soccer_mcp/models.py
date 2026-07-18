"""
brazilian_soccer_mcp.models
===========================

Core domain dataclasses for the Brazilian Soccer MCP server.

Context
-------
This package implements a Model Context Protocol (MCP) server that exposes a
*knowledge graph interface* over Brazilian soccer datasets (matches, players,
teams, competitions). The dataclasses in this module are the typed records that
flow through every layer:

    CSV  ->  data_loader  ->  Match / Player records  ->  KnowledgeGraph
                                                              |
                                                              v
                                                         QueryEngine
                                                              |
                                                              v
                                                        MCP tools (server.py)

Design notes
------------
* Records are plain ``dataclass`` objects (frozen=False) so the loader can fill
  them row-by-row without fighting immutability, but they are treated as
  read-only once published into the graph.
* Every numeric field that can be missing in the raw data (goals, corners, ...)
  is typed ``Optional`` and stored as ``None`` rather than ``NaN`` so the values
  are always JSON-serialisable for MCP responses.
* ``Node`` and ``Edge`` are the primitive graph types. The knowledge graph is
  deliberately simple (adjacency lists keyed by node id) — enough to model the
  relationships required by the spec (team<->match, player->club,
  match->competition/season) and to answer traversal-style questions such as
  "which competitions has Palmeiras played in?".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Domain records
# ---------------------------------------------------------------------------


@dataclass
class Match:
    """A single soccer match, normalised across all source CSV files."""

    id: str
    competition: str                       # canonical competition name
    season: Optional[int]                  # year of the season
    date: Optional[date] = None            # match date (no time)
    datetime: Optional[datetime] = None    # full kick-off timestamp if known
    home_team: str = ""                    # canonical home team name
    away_team: str = ""                    # canonical away team name
    home_goals: Optional[int] = None
    away_goals: Optional[int] = None
    round: Optional[str] = None            # round number / cup round / stage
    stage: Optional[str] = None            # tournament stage (Libertadores)
    arena: Optional[str] = None            # stadium (novo dataset)
    source_file: str = ""                  # which CSV the row came from
    # Extended statistics (only populated from BR-Football-Dataset.csv)
    home_corners: Optional[float] = None
    away_corners: Optional[float] = None
    home_shots: Optional[float] = None
    away_shots: Optional[float] = None
    home_attacks: Optional[float] = None
    away_attacks: Optional[float] = None

    # --- derived helpers ---------------------------------------------------

    @property
    def result(self) -> str:
        """``"home_win"`` / ``"away_win"`` / ``"draw"`` / ``"unknown"``."""
        if self.home_goals is None or self.away_goals is None:
            return "unknown"
        if self.home_goals > self.away_goals:
            return "home_win"
        if self.home_goals < self.away_goals:
            return "away_win"
        return "draw"

    @property
    def goal_difference(self) -> Optional[int]:
        if self.home_goals is None or self.away_goals is None:
            return None
        return self.home_goals - self.away_goals

    @property
    def winner(self) -> Optional[str]:
        """Canonical name of the winning team, or ``None`` for a draw."""
        r = self.result
        if r == "home_win":
            return self.home_team
        if r == "away_win":
            return self.away_team
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "date": self.date.isoformat() if self.date else None,
            "competition": self.competition,
            "season": self.season,
            "round": self.round,
            "stage": self.stage,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_goals": self.home_goals,
            "away_goals": self.away_goals,
            "result": self.result,
            "venue": None,
            "source": self.source_file,
        }


@dataclass
class Player:
    """A FIFA player record (from ``fifa_data.csv``)."""

    id: int
    name: str
    age: Optional[int] = None
    nationality: str = ""
    overall: Optional[int] = None
    potential: Optional[int] = None
    club: str = ""
    position: str = ""
    jersey_number: Optional[int] = None
    height: Optional[str] = None          # raw FIFA form e.g. "5'9"
    weight: Optional[str] = None          # raw FIFA form e.g. "159lbs"
    preferred_foot: Optional[str] = None
    # selected skill ratings
    crossing: Optional[int] = None
    finishing: Optional[int] = None
    dribbling: Optional[int] = None
    short_passing: Optional[int] = None
    heading_accuracy: Optional[int] = None
    shot_power: Optional[int] = None
    value: Optional[str] = None           # raw e.g. "€110.5M"
    wage: Optional[str] = None            # raw e.g. "€565K"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "age": self.age,
            "nationality": self.nationality,
            "overall": self.overall,
            "potential": self.potential,
            "club": self.club,
            "position": self.position,
            "jersey_number": self.jersey_number,
            "height": self.height,
            "weight": self.weight,
            "preferred_foot": self.preferred_foot,
            "value": self.value,
            "wage": self.wage,
        }


@dataclass
class Team:
    """A team node in the knowledge graph."""

    name: str                            # canonical display name
    aliases: set[str] = field(default_factory=set)
    state: Optional[str] = None          # Brazilian state (UF) if known

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state,
            "aliases": sorted(self.aliases),
        }


@dataclass
class Competition:
    """A competition node (e.g. Brasileirão Serie A, Copa do Brasil)."""

    name: str
    seasons: set[int] = field(default_factory=set)
    match_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "seasons": sorted(self.seasons),
            "match_count": self.match_count,
        }


# ---------------------------------------------------------------------------
# Graph primitives
# ---------------------------------------------------------------------------


@dataclass
class Node:
    """A node in the knowledge graph."""

    id: str
    type: str                             # "team" | "player" | "match" | "competition" | "season"
    label: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class Edge:
    """A directed edge between two graph nodes."""

    source: str                           # node id
    target: str                           # node id
    type: str                             # relationship type
    properties: dict[str, Any] = field(default_factory=dict)
