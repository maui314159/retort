"""In-memory knowledge graph over the loaded dataset.

Context
-------
The spec calls for a *knowledge graph interface* for Brazilian soccer data.
Rather than require an external graph database (Neo4j) that may not be
available at test time, we build a lightweight in-memory graph in pure
Python:

* **Nodes** of four kinds — :class:`TeamNode`, :class:`PlayerNode`,
  :class:`MatchNode`, :class:`CompetitionNode` — each carrying an index of
  back-references to the edges that touch them.
* **Edges** — ``HOME_IN`` / ``AWAY_IN`` (team → match), ``PLAYED_FOR``
  (player → club/team), ``IN_COMPETITION`` (match → competition).

The graph is queried through the :mod:`brazilian_soccer_mcp.queries`
module, which uses these adjacency indexes for O(degree) lookups instead of
scanning the whole match list.

Team identity is the **canonical display name** produced by the
:class:`~brazilian_soccer_mcp.normalize.TeamNameNormalizer`, so every node
key and every match's ``home_team`` / ``away_team`` field share one stable
spelling.  Matching is therefore plain string equality.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from .loader import Dataset
from .models import MatchRecord, PlayerRecord


@dataclass
class TeamNode:
    name: str
    matches: list[MatchRecord] = field(default_factory=list)
    players: list[PlayerRecord] = field(default_factory=list)


@dataclass
class PlayerNode:
    record: PlayerRecord


@dataclass
class CompetitionNode:
    name: str
    matches: list[MatchRecord] = field(default_factory=list)


class KnowledgeGraph:
    """Adjacency-list knowledge graph built from a :class:`Dataset`."""

    def __init__(self, dataset: Dataset) -> None:
        self.dataset = dataset
        self.teams: dict[str, TeamNode] = {}
        self.players: dict[int, PlayerNode] = {}
        self.competitions: dict[str, CompetitionNode] = {}
        self._build()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _team(self, name: str) -> TeamNode:
        node = self.teams.get(name)
        if node is None:
            node = TeamNode(name=name)
            self.teams[name] = node
        return node

    def _competition(self, name: str) -> CompetitionNode:
        node = self.competitions.get(name)
        if node is None:
            node = CompetitionNode(name=name)
            self.competitions[name] = node
        return node

    def _build(self) -> None:
        normalizer = self.dataset.normalizer
        # Match edges.
        for m in self.dataset.matches:
            home = self._team(m.home_team)
            away = self._team(m.away_team)
            comp = self._competition(m.competition)
            home.matches.append(m)
            away.matches.append(m)
            comp.matches.append(m)
        # Player -> club edges.  The FIFA "Club" column uses spellings that
        # do not always match the match-data team names exactly; the
        # normalizer resolves them to the canonical club when possible and
        # otherwise registers the raw spelling so the club is at least
        # addressable as a TeamNode.
        for p in self.dataset.players:
            self.players[p.id] = PlayerNode(record=p)
            if p.club:
                team_name = normalizer.canonical(p.club)
                if team_name is None:
                    team_name = normalizer.register(p.club)
                if team_name:
                    self._team(team_name).players.append(p)

    # ------------------------------------------------------------------
    # Lookup helpers used by the query layer
    # ------------------------------------------------------------------

    def resolve_team(self, name: str) -> Optional[TeamNode]:
        """Resolve any spelling to the canonical :class:`TeamNode`."""

        canonical = self.dataset.normalizer.canonical(name)
        if canonical is None:
            return None
        return self.teams.get(canonical)

    def team_matches(
        self,
        name: str,
        role: str = "either",
    ) -> list[MatchRecord]:
        """Return matches for *name* filtered by ``role`` (home/away/either)."""

        canonical = self.dataset.normalizer.canonical(name)
        if canonical is None:
            return []
        node = self.teams.get(canonical)
        if node is None:
            return []
        if role == "either":
            return list(node.matches)
        out: list[MatchRecord] = []
        for m in node.matches:
            if role == "home" and m.home_team != canonical:
                continue
            if role == "away" and m.away_team != canonical:
                continue
            out.append(m)
        return out

    def head_to_head(self, a: str, b: str) -> list[MatchRecord]:
        """Matches where *a* and *b* played each other (any venue)."""

        canon_a = self.dataset.normalizer.canonical(a)
        canon_b = self.dataset.normalizer.canonical(b)
        if canon_a is None or canon_b is None:
            return []
        node_a = self.teams.get(canon_a)
        if node_a is None:
            return []
        out: list[MatchRecord] = []
        seen: set[int] = set()
        for m in node_a.matches:
            opp = m.away_team if m.home_team == canon_a else m.home_team
            if opp == canon_b:
                mid = id(m)
                if mid not in seen:
                    seen.add(mid)
                    out.append(m)
        out.sort(key=lambda m: (m.date or __import__("datetime").date.min))
        return out

    def competition(self, name: str) -> Optional[CompetitionNode]:
        exact = self.competitions.get(name)
        if exact is not None:
            return exact
        # Accent/case-insensitive fallback.
        from .normalize import _fold

        folded = _fold(name)
        for cname, node in self.competitions.items():
            if _fold(cname) == folded:
                return node
        return None

    def list_teams(self) -> list[str]:
        return sorted(self.teams)

    def list_competitions(self) -> list[str]:
        return sorted(self.competitions)
