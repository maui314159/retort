"""
Context Block
=============

Module: brazilian_soccer_mcp.knowledge_graph
Purpose: Build an in-memory knowledge graph from the unified
         ``MatchRecord`` and ``PlayerRecord`` objects produced by
         ``DataLoader``.

Graph schema
-------------
Nodes:
  * TeamNode        - keyed by normalised team name (match_key)
  * PlayerNode      - keyed by FIFA player ID
  * MatchNode       - keyed by match_id
  * CompetitionNode - keyed by canonical competition name

Edges (stored as adjacency lists):
  * PLAYED_HOME   : MatchNode -> TeamNode
  * PLAYED_AWAY   : MatchNode -> TeamNode
  * IN_COMPETITION: MatchNode -> CompetitionNode
  * MEMBER_OF     : PlayerNode -> TeamNode   (via club_key)
  * NATIONALITY  : PlayerNode -> str        (indexed separately)

In addition to the explicit graph, the class maintains fast lookup
indexes so that the query layer can answer questions in well under
the performance budgets required by the spec (2 s for simple
lookups, 5 s for aggregates).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from .data_loader import DataLoader, MatchRecord, PlayerRecord


# ---------------------------------------------------------------------------
# Node types
# ---------------------------------------------------------------------------
@dataclass
class TeamNode:
    """A team node in the knowledge graph."""

    key: str                       # normalised match key
    display_name: str = ""         # best-known display name
    states: set[str] = field(default_factory=set)
    home_matches: list[MatchRecord] = field(default_factory=list)
    away_matches: list[MatchRecord] = field(default_factory=list)

    @property
    def all_matches(self) -> list[MatchRecord]:
        return self.home_matches + self.away_matches

    @property
    def match_count(self) -> int:
        return len(self.home_matches) + len(self.away_matches)


@dataclass
class CompetitionNode:
    """A competition node in the knowledge graph."""

    name: str
    matches: list[MatchRecord] = field(default_factory=list)
    seasons: set[int] = field(default_factory=set)

    @property
    def match_count(self) -> int:
        return len(self.matches)


@dataclass
class MatchNode:
    """A match node in the knowledge graph."""

    record: MatchRecord
    home_team: Optional[TeamNode] = None
    away_team: Optional[TeamNode] = None
    competition: Optional[CompetitionNode] = None


@dataclass
class PlayerNode:
    """A player node in the knowledge graph."""

    record: PlayerRecord
    team: Optional[TeamNode] = None  # linked via club_key


# ---------------------------------------------------------------------------
# Knowledge graph
# ---------------------------------------------------------------------------
class KnowledgeGraph:
    """In-memory knowledge graph of Brazilian soccer data.

    Built from a ``DataLoader`` instance.  Provides indexed access to
    teams, players, matches, and competitions for the query engine.
    """

    def __init__(self, loader: DataLoader):
        self.loader = loader
        # Node stores
        self.teams: dict[str, TeamNode] = {}
        self.players: dict[int, PlayerNode] = {}
        self.matches: dict[str, MatchNode] = {}
        self.competitions: dict[str, CompetitionNode] = {}
        # Indexes
        self._players_by_name: dict[str, list[PlayerNode]] = defaultdict(list)
        self._players_by_nationality: dict[str, list[PlayerNode]] = defaultdict(list)
        self._players_by_club_key: dict[str, list[PlayerNode]] = defaultdict(list)
        self._matches_by_season: dict[int, list[MatchRecord]] = defaultdict(list)
        self._build()

    # -- construction -------------------------------------------------------
    def _build(self) -> None:
        self._build_competitions()
        self._build_teams_and_matches()
        self._build_players()

    def _build_competitions(self) -> None:
        for m in self.loader.matches:
            comp = self.competitions.setdefault(
                m.competition, CompetitionNode(name=m.competition)
            )
            comp.matches.append(m)
            if m.season is not None:
                comp.seasons.add(m.season)
            self._matches_by_season[m.season].append(m) if m.season else None

    def _build_teams_and_matches(self) -> None:
        for m in self.loader.matches:
            # Home team
            if m.home_team_key:
                team = self.teams.setdefault(
                    m.home_team_key, TeamNode(key=m.home_team_key)
                )
                if m.home_team and not team.display_name:
                    team.display_name = m.home_team
                elif m.home_team:
                    # Prefer the shortest display name (usually the
                    # most common short form)
                    if len(m.home_team) < len(team.display_name):
                        team.display_name = m.home_team
                if m.home_state:
                    team.states.add(m.home_state)
                team.home_matches.append(m)

            # Away team
            if m.away_team_key:
                team = self.teams.setdefault(
                    m.away_team_key, TeamNode(key=m.away_team_key)
                )
                if m.away_team and not team.display_name:
                    team.display_name = m.away_team
                elif m.away_team and len(m.away_team) < len(team.display_name):
                    team.display_name = m.away_team
                if m.away_state:
                    team.states.add(m.away_state)
                team.away_matches.append(m)

            # Match node
            mn = MatchNode(record=m)
            mn.home_team = self.teams.get(m.home_team_key)
            mn.away_team = self.teams.get(m.away_team_key)
            mn.competition = self.competitions.get(m.competition)
            self.matches[m.match_id] = mn

    def _build_players(self) -> None:
        for p in self.loader.players:
            pn = PlayerNode(record=p)
            self.players[p.player_id] = pn
            self._players_by_name[p.name.lower()].append(pn)
            self._players_by_nationality[p.nationality].append(pn)
            if p.club_key:
                self._players_by_club_key[p.club_key].append(pn)
                # Link to team node if it exists
                if p.club_key in self.teams:
                    pn.team = self.teams[p.club_key]

    # -- lookups -----------------------------------------------------------
    def get_team(self, name: str) -> Optional[TeamNode]:
        """Look up a team by any name variant.

        Uses ``team_match_key`` to normalise the input, then returns
        the matching ``TeamNode`` or ``None``.
        """
        from .normalizer import team_match_key
        key = team_match_key(name)
        return self.teams.get(key)

    def find_teams(self, name: str) -> list[TeamNode]:
        """Find all teams whose key matches the given name.

        If the name normalises to a key that exists, returns that
        team.  Otherwise, does a prefix/substring search and returns
        all matches.
        """
        from .normalizer import team_match_key
        key = team_match_key(name)
        if key in self.teams:
            return [self.teams[key]]
        # Substring search on keys
        results = []
        for tkey, team in self.teams.items():
            if key and key in tkey:
                results.append(team)
            elif name.lower() in tkey:
                results.append(team)
        return results

    def get_competition(self, name: str) -> Optional[CompetitionNode]:
        """Look up a competition by name (case-insensitive)."""
        name_lower = name.lower().strip()
        for cname, comp in self.competitions.items():
            if cname.lower() == name_lower:
                return comp
        # Fuzzy: partial match
        for cname, comp in self.competitions.items():
            if name_lower in cname.lower() or cname.lower() in name_lower:
                return comp
        return None

    def find_players_by_name(self, name: str) -> list[PlayerNode]:
        """Find players whose name contains the query (case-insensitive)."""
        name_lower = name.lower().strip()
        if name_lower in self._players_by_name:
            return list(self._players_by_name[name_lower])
        # Substring search
        results = []
        for pname, players in self._players_by_name.items():
            if name_lower in pname:
                results.extend(players)
        return results

    def find_players_by_nationality(self, nationality: str) -> list[PlayerNode]:
        """Find players by nationality (case-insensitive)."""
        nat_lower = nationality.lower().strip()
        results = []
        for nat, players in self._players_by_nationality.items():
            if nat == nat_lower:
                results.extend(players)
        return results

    def find_players_by_club(self, club: str) -> list[PlayerNode]:
        """Find players by club name (uses normalised club key)."""
        from .normalizer import team_match_key
        key = team_match_key(club)
        if key in self._players_by_club_key:
            return list(self._players_by_club_key[key])
        # Substring search on club names
        results = []
        for ckey, players in self._players_by_club_key.items():
            if key and key in ckey:
                results.extend(players)
        return results

    def all_team_keys(self) -> list[str]:
        """Return all team keys sorted alphabetically."""
        return sorted(self.teams.keys())

    def all_competition_names(self) -> list[str]:
        """Return all competition names."""
        return sorted(self.competitions.keys())
