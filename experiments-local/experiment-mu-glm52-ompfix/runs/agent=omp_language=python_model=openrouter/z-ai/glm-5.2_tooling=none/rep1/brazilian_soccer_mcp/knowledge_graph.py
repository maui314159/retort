"""
brazilian_soccer_mcp.knowledge_graph
====================================

In-memory knowledge graph for Brazilian soccer data.

Context
-------
The spec calls for a *knowledge graph interface* over the datasets. This module
builds that graph from the normalised :class:`Match` and :class:`Player`
records produced by :mod:`brazilian_soccer_mcp.data_loader`.

Graph model
-----------
Node types:
  * ``team``        — one per canonical team name
  * ``player``      — one per FIFA player
  * ``match``       — one per match record
  * ``competition`` — one per competition (Brasileirão Serie A, Copa do Brasil, …)
  * ``season``      — one per (competition, season) pair

Edge types (directed, ``source -> target``):
  * ``PLAYED_HOME``   team  -> match
  * ``PLAYED_AWAY``   team  -> match
  * ``PARTICIPATED``  player -> team   (FIFA club assignment)
  * ``BELONGS_TO``    match -> competition
  * ``HELD_IN``       match -> season
  * ``COMPETED_IN``   team  -> competition  (deduced from match participation)
  * ``HAS_SEASON``    competition -> season

Indexes
-------
For sub-second query performance the graph maintains:
  * ``_matches_by_team``      — canonical team name -> list[Match]
  * ``_matches_by_competition``— competition -> list[Match]
  * ``_matches_by_season``    — (competition, season) -> list[Match]
  * ``_players_by_club``      — FIFA club name -> list[Player]
  * ``_players_by_nationality``— nationality -> list[Player]
  * ``_h2h``                  — frozenset({team_a, team_b}) -> list[Match]

All indexes are built once at construction time.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Optional

from .data_loader import LoadedData
from .models import Competition, Edge, Match, Node, Player, Team


class KnowledgeGraph:
    """In-memory knowledge graph with pre-built lookup indexes."""

    def __init__(self, data: LoadedData) -> None:
        self.data = data
        self.normalizer = data.normalizer

        # nodes
        self.nodes: dict[str, Node] = {}
        self.teams: dict[str, Team] = {}
        self.players: dict[int, Player] = {}
        self.competitions: dict[str, Competition] = {}

        # edges (adjacency lists)
        self.edges_out: dict[str, list[Edge]] = defaultdict(list)
        self.edges_in: dict[str, list[Edge]] = defaultdict(list)

        # indexes
        self._matches_by_team: dict[str, list[Match]] = defaultdict(list)
        self._matches_by_competition: dict[str, list[Match]] = defaultdict(list)
        self._matches_by_season: dict[tuple[str, int], list[Match]] = defaultdict(list)
        self._h2h: dict[frozenset[str], list[Match]] = defaultdict(list)
        self._players_by_club: dict[str, list[Player]] = defaultdict(list)
        self._players_by_nationality: dict[str, list[Player]] = defaultdict(list)

        self._build()

    # ------------------------------------------------------------------
    # Building
    # ------------------------------------------------------------------

    def _team_node_id(self, name: str) -> str:
        return f"team:{name}"

    def _player_node_id(self, pid: int) -> str:
        return f"player:{pid}"

    def _match_node_id(self, mid: str) -> str:
        return f"match:{mid}"

    def _comp_node_id(self, name: str) -> str:
        return f"comp:{name}"

    def _season_node_id(self, comp: str, season: int) -> str:
        return f"season:{comp}:{season}"

    def _add_node(self, node: Node) -> None:
        if node.id not in self.nodes:
            self.nodes[node.id] = node

    def _add_edge(self, edge: Edge) -> None:
        self.edges_out[edge.source].append(edge)
        self.edges_in[edge.target].append(edge)

    def _build(self) -> None:
        # --- teams from matches ---
        team_comps: dict[str, set[str]] = defaultdict(set)
        for m in self.data.matches:
            team_comps[m.home_team].add(m.competition)
            team_comps[m.away_team].add(m.competition)

        for name, comps in team_comps.items():
            self.teams[name] = Team(name=name)
            self._add_node(Node(
                id=self._team_node_id(name), type="team", label=name,
                properties={"competitions": sorted(comps)},
            ))

        # --- players ---
        for p in self.data.players:
            self.players[p.id] = p
            self._add_node(Node(
                id=self._player_node_id(p.id), type="player", label=p.name,
                properties=p.to_dict(),
            ))
            if p.club:
                self._players_by_club[p.club].append(p)
            if p.nationality:
                self._players_by_nationality[p.nationality].append(p)

        # --- competitions + seasons + matches ---
        for m in self.data.matches:
            # competition node
            if m.competition not in self.competitions:
                self.competitions[m.competition] = Competition(name=m.competition)
                self._add_node(Node(
                    id=self._comp_node_id(m.competition), type="competition",
                    label=m.competition, properties={},
                ))
            comp = self.competitions[m.competition]
            comp.match_count += 1
            if m.season is not None:
                comp.seasons.add(m.season)

            # match node
            self._add_node(Node(
                id=self._match_node_id(m.id), type="match",
                label=f"{m.home_team} vs {m.away_team}",
                properties=m.to_dict(),
            ))

            # edges: team -> match
            self._add_edge(Edge(
                source=self._team_node_id(m.home_team),
                target=self._match_node_id(m.id),
                type="PLAYED_HOME",
            ))
            self._add_edge(Edge(
                source=self._team_node_id(m.away_team),
                target=self._match_node_id(m.id),
                type="PLAYED_AWAY",
            ))
            # edges: match -> competition / season
            self._add_edge(Edge(
                source=self._match_node_id(m.id),
                target=self._comp_node_id(m.competition),
                type="BELONGS_TO",
            ))
            if m.season is not None:
                sid = self._season_node_id(m.competition, m.season)
                self._add_node(Node(id=sid, type="season",
                                    label=f"{m.competition} {m.season}", properties={}))
                self._add_edge(Edge(
                    source=self._match_node_id(m.id), target=sid, type="HELD_IN",
                ))
                self._add_edge(Edge(
                    source=self._comp_node_id(m.competition), target=sid,
                    type="HAS_SEASON",
                ))

            # edges: team -> competition
            self._add_edge(Edge(
                source=self._team_node_id(m.home_team),
                target=self._comp_node_id(m.competition),
                type="COMPETED_IN",
            ))
            self._add_edge(Edge(
                source=self._team_node_id(m.away_team),
                target=self._comp_node_id(m.competition),
                type="COMPETED_IN",
            ))

            # indexes
            self._matches_by_team[m.home_team].append(m)
            self._matches_by_team[m.away_team].append(m)
            self._matches_by_competition[m.competition].append(m)
            if m.season is not None:
                self._matches_by_season[(m.competition, m.season)].append(m)
            if m.home_team and m.away_team and m.home_team != m.away_team:
                key = frozenset({m.home_team, m.away_team})
                self._h2h[key].append(m)

        # --- player -> team edges (FIFA club -> canonical team name) ---
        for p in self.data.players:
            if not p.club:
                continue
            canonical = self.normalizer.canonical(p.club) if self.normalizer else p.club
            if canonical in self.teams:
                self._add_edge(Edge(
                    source=self._player_node_id(p.id),
                    target=self._team_node_id(canonical),
                    type="PARTICIPATED",
                    properties={"club_raw": p.club},
                ))

    # ------------------------------------------------------------------
    # Public lookup helpers (used by the query engine)
    # ------------------------------------------------------------------

    def resolve_team(self, query: str) -> Optional[str]:
        """Resolve a user-provided team name to a canonical team name.

        Tries exact match first, then normalizer, then case-insensitive
        substring search across all known teams.
        """
        if not query:
            return None
        # exact
        if query in self.teams:
            return query
        # via normalizer
        if self.normalizer:
            canonical = self.normalizer.canonical(query)
            if canonical in self.teams:
                return canonical
        # case-insensitive substring
        q = query.lower()
        matches = [t for t in self.teams if q in t.lower()]
        if len(matches) == 1:
            return matches[0]
        # try accent-insensitive
        from .normalize import make_key
        qk = make_key(query)
        exact_key = [t for t in self.teams if make_key(t) == qk]
        if len(exact_key) == 1:
            return exact_key[0]
        return None

    def matches_for_team(
        self,
        team: str,
        competition: Optional[str] = None,
        season: Optional[int] = None,
    ) -> list[Match]:
        """All matches involving ``team``, optionally filtered."""
        result = self._matches_by_team.get(team, [])
        if competition is not None:
            result = [m for m in result if m.competition == competition]
        if season is not None:
            result = [m for m in result if m.season == season]
        return result

    def head_to_head(self, team_a: str, team_b: str) -> list[Match]:
        return self._h2h.get(frozenset({team_a, team_b}), [])

    def competition_seasons(self, competition: str) -> list[int]:
        comp = self.competitions.get(competition)
        return sorted(comp.seasons) if comp else []

    def matches_for_competition(
        self,
        competition: str,
        season: Optional[int] = None,
    ) -> list[Match]:
        if season is not None:
            return self._matches_by_season.get((competition, season), [])
        return self._matches_by_competition.get(competition, [])

    def players_for_club(self, club: str) -> list[Player]:
        """Players whose FIFA club matches ``club`` (normalised)."""
        if not club:
            return []
        canonical = self.normalizer.canonical(club) if self.normalizer else club
        # try canonical, then raw, then substring
        result = self._players_by_club.get(canonical, [])
        if not result:
            result = self._players_by_club.get(club, [])
        if not result:
            cl = club.lower()
            for c, ps in self._players_by_club.items():
                if cl in c.lower():
                    result = result + ps
        return result

    def players_for_nationality(self, nationality: str) -> list[Player]:
        return self._players_by_nationality.get(nationality, [])

    # ------------------------------------------------------------------
    # Graph introspection
    # ------------------------------------------------------------------

    def node_count(self) -> int:
        return len(self.nodes)

    def edge_count(self) -> int:
        return sum(len(v) for v in self.edges_out.values())

    def team_count(self) -> int:
        return len(self.teams)

    def match_count(self) -> int:
        return len(self.data.matches)

    def player_count(self) -> int:
        return len(self.players)

    def competitions_list(self) -> list[str]:
        return sorted(self.competitions.keys())

    def team_names(self) -> list[str]:
        return sorted(self.teams.keys())
