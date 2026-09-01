"""
 brazilian_soccer_mcp / models.py
 ================================

 Why
 ---
 The loader, query layer, renderer, MCP tools and tests all need to agree
 on the shape of a "match", "player", "club" and "standing row".  Keeping
 those shapes in one small module (plain dataclasses, JSON-ready
 ``to_dict()``) makes every other module thinner and the whole graph
 serialisable over the MCP wire.

 What
 ---
 * :class:`Match`      - one fixture: canonical competition id, season,
                         date, both clubs (display name + canonical key),
                         goals (None = scheduled, not played), round/stage,
                         venue, source CSV and (BR-Football only) extended
                         stats (corners, shots, attacks, half-time results).
 * :class:`Player`     - one FIFA player row: identity, ratings, club,
                         position, physical/skill attributes, value/wage.
 * :class:`Club`       - registry entry: canonical key, core, region, best
                         display name, every raw spelling seen, match
                         counts, seasons and competitions covered.
 * :class:`StandingRow`- one table line: position, points, W/D/L, goals.

 All dataclasses are frozen-free (loader fills them in) but hashable by
 key where needed.  ``to_dict()`` output is what MCP tools return as
 ``structuredContent``.

 Test: covered via ``tests/test_loader.py`` and the query feature tests.
======================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Match:
    """A single fixture, post-normalisation and post-dedup."""

    competition: str  # canonical id, e.g. "serie_a"
    competition_display: str  # e.g. "Brasileirão Série A"
    season: int | None
    date: object | None  # datetime.date | None
    time: str | None  # "20:00"
    home: str  # display name
    away: str
    home_key: str  # canonical key, e.g. "flamengo|RJ"
    away_key: str
    home_goals: int | None  # None = scheduled, not played
    away_goals: int | None
    round: str | None  # "22" for leagues/cup rounds
    stage: str | None  # Libertadores: "group stage"...
    venue: str | None  # novo dataset: stadium name
    source: str  # source CSV file name
    stats: dict | None = None  # BR-Football extended stats

    @property
    def played(self) -> bool:
        return self.home_goals is not None and self.away_goals is not None

    @property
    def score(self) -> str:
        if self.played:
            return f"{self.home_goals}-{self.away_goals}"
        return "not played"

    @property
    def phase(self) -> str | None:
        """Human-friendly round/stage label."""
        if self.stage:
            return self.stage.title()
        if self.round:
            return f"Round {self.round}"
        return None

    def to_dict(self) -> dict:
        return {
            "competition": self.competition,
            "competition_display": self.competition_display,
            "season": self.season,
            "date": self.date.isoformat() if self.date else None,
            "time": self.time,
            "home": self.home,
            "away": self.away,
            "home_key": self.home_key,
            "away_key": self.away_key,
            "home_goals": self.home_goals,
            "away_goals": self.away_goals,
            "score": self.score,
            "round": self.round,
            "stage": self.stage,
            "phase": self.phase,
            "venue": self.venue,
            "source": self.source,
            "stats": self.stats,
        }


@dataclass
class Player:
    """One FIFA-database player."""

    player_id: int | None
    name: str
    age: int | None
    nationality: str
    overall: int
    potential: int
    club: str | None
    position: str | None
    jersey: int | None
    preferred_foot: str | None
    value: str | None
    wage: str | None
    value_eur: int | None
    wage_eur: int | None
    height: str | None
    weight: str | None
    skills: dict[str, int] = field(default_factory=dict)

    def to_dict(self, include_skills: bool = False) -> dict:
        data = {
            "id": self.player_id,
            "name": self.name,
            "age": self.age,
            "nationality": self.nationality,
            "overall": self.overall,
            "potential": self.potential,
            "club": self.club,
            "position": self.position,
            "jersey": self.jersey,
            "preferred_foot": self.preferred_foot,
            "value": self.value,
            "wage": self.wage,
            "height": self.height,
            "weight": self.weight,
        }
        if include_skills:
            data["skills"] = self.skills
        return data


@dataclass
class Club:
    """Registry entry for one club (node of the knowledge graph)."""

    key: str  # "flamengo|RJ"
    core: str  # "flamengo"
    state: str | None  # "RJ"
    country: str | None  # "URU" for foreign clubs
    display: str  # best display name
    variants: list[str] = field(default_factory=list)  # raw spellings seen
    match_count: int = 0  # deduped matches involving the club
    played_count: int = 0
    competitions: list[str] = field(default_factory=list)  # canonical ids
    seasons: list[int] = field(default_factory=list)

    @property
    def region(self) -> str | None:
        return self.state or self.country

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "name": self.display,
            "core": self.core,
            "state": self.state,
            "country": self.country,
            "match_count": self.match_count,
            "played_count": self.played_count,
            "competitions": self.competitions,
            "first_season": min(self.seasons) if self.seasons else None,
            "last_season": max(self.seasons) if self.seasons else None,
            "name_variations": self.variants,
        }


@dataclass
class StandingRow:
    """One line of a computed league table."""

    position: int
    team: str  # display name
    team_key: str
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_diff: int
    points: int

    def to_dict(self) -> dict:
        return {
            "position": self.position,
            "team": self.team,
            "played": self.played,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses,
            "goals_for": self.goals_for,
            "goals_against": self.goals_against,
            "goal_diff": self.goal_diff,
            "points": self.points,
        }
