# SPDX-License-Identifier: Apache-2.0
# Context block ----------------------------------------------------------------
# Module: brazilian_soccer_mcp.models
# Purpose: Typed dataclasses for the entities surfaced by the MCP server.
# Design notes:
#   * Match is a single normalized row spanning all 6 CSV sources so callers
#     never need to know which file a record came from.
#   * Home/away goals are optional because some raw rows are blank in the
#     Cup dataset (matches that ended 0-0 vs. not-yet-played).
#   * We store both the raw home/away team strings (for display) and the
#     canonical normalized keys (for matching/joins).
#   * TeamStats / Standings are precomputed aggregate views returned by the
#     query layer.
# --------------------------------------------------------------------------- #
"""Typed dataclasses for matches, players, and aggregated statistics."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass(frozen=True)
class Match:
    """A single normalized match record from any of the CSV files."""

    date: date | None
    datetime: datetime | None
    home_team: str
    away_team: str
    home_team_key: str
    away_team_key: str
    home_goal: int | None
    away_goal: int | None
    competition: str
    season: int | None
    round_info: str | None
    stage: str | None
    stadium: str | None
    source_file: str

    @property
    def score_str(self) -> str:
        hg = "-" if self.home_goal is None else self.home_goal
        ag = "-" if self.away_goal is None else self.away_goal
        return f"{hg}-{ag}"

    def winner_key(self) -> str | None:
        """Return the canonical key of the winner, or "" for a draw.

        Returns ``None`` if the score is unknown (match not yet played or
        data missing). Returns ``""`` (empty) for an exact draw.
        """
        if self.home_goal is None or self.away_goal is None:
            return None
        if self.home_goal > self.away_goal:
            return self.home_team_key
        if self.away_goal > self.home_goal:
            return self.away_team_key
        return ""

    def is_draw(self) -> bool:
        if self.home_goal is None or self.away_goal is None:
            return False
        return self.home_goal == self.away_goal


@dataclass(frozen=True)
class Player:
    """A single FIFA player row, lightly typed."""

    player_id: int
    name: str
    age: int | None
    nationality: str
    overall: int | None
    potential: int | None
    club: str
    club_key: str
    position: str | None
    jersey_number: int | None
    height: str | None
    weight: str | None
    preferred_foot: str | None
    value: str | None
    wage: str | None

    # A subset of FIFA skill ratings we expose for queries. Kept as a dict so
    # the MCP tool surface can return whichever the caller asks for without
    # bloating the dataclass.
    attributes: dict[str, int] = field(default_factory=dict)


@dataclass
class TeamStats:
    """Aggregate win/draw/loss/goal record for a team over a set of matches."""

    team_key: str
    display_name: str
    matches: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    home_matches: int = 0
    home_wins: int = 0
    home_draws: int = 0
    home_losses: int = 0
    home_goals_for: int = 0
    home_goals_against: int = 0
    away_matches: int = 0
    away_wins: int = 0
    away_draws: int = 0
    away_losses: int = 0
    away_goals_for: int = 0
    away_goals_against: int = 0

    @property
    def win_rate(self) -> float:
        return (self.wins / self.matches) if self.matches else 0.0

    @property
    def home_win_rate(self) -> float:
        return (self.home_wins / self.home_matches) if self.home_matches else 0.0

    @property
    def away_win_rate(self) -> float:
        return (self.away_wins / self.away_matches) if self.away_matches else 0.0

    @property
    def points(self) -> int:
        """League-style points (3 per win, 1 per draw)."""
        return 3 * self.wins + self.draws


@dataclass
class Standing:
    """A single row in a calculated league standings table."""

    team_key: str
    display_name: str
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_diff: int
    points: int

    def as_dict(self) -> dict:
        return {
            "team": self.display_name,
            "team_key": self.team_key,
            "played": self.played,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses,
            "goals_for": self.goals_for,
            "goals_against": self.goals_against,
            "goal_diff": self.goal_diff,
            "points": self.points,
        }


@dataclass
class HeadToHead:
    """Head-to-head record between two canonical teams."""

    team_a_key: str
    team_b_key: str
    team_a_wins: int = 0
    team_b_wins: int = 0
    draws: int = 0
    team_a_goals: int = 0
    team_b_goals: int = 0
    matches: int = 0
