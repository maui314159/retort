"""In-memory knowledge graph for Brazilian soccer data.

Context
-------
TASK.md asks for an MCP server that provides a *knowledge graph interface* for
Brazilian soccer.  Rather than require an external graph database (e.g. Neo4j),
this module implements a small, dependency-free in-memory property graph that is
built once at load time from the CSV datasets.

Nodes are typed entities (``Team``, ``Player``, ``Match``, ``Competition``,
``Season``) and edges describe the relationships between them
(``PLAYED_IN``, ``PARTICIPATED_IN``, ``HELD_IN``, ``WON``, ``DREW``, ``LOST``).
The query layer in ``queries.py`` walks this graph (and the parallel record
lists) to answer natural-language questions.

The graph is the conceptual API; record lists remain the fast path for
aggregations, but the graph gives the "knowledge graph interface" the spec
calls for and lets us answer relationship queries such as
"What competitions has Palmeiras played in?".
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .normalize import team_key


@dataclass
class Node:
    """A node in the knowledge graph."""

    id: str
    type: str  # team | player | match | competition | season
    label: str
    properties: Dict[str, Any] = field(default_factory=dict)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Node) and self.id == other.id and self.type == other.type

    def __hash__(self) -> int:
        return hash((self.type, self.id))


@dataclass
class Edge:
    """A directed edge between two nodes."""

    source: str  # node id
    target: str  # node id
    relation: str  # e.g. PLAYED_IN, WON, LOST, DREW, PARTICIPATED_IN, HELD_IN
    properties: Dict[str, Any] = field(default_factory=dict)


class KnowledgeGraph:
    """A simple property graph over teams, players, matches, competitions."""

    def __init__(self) -> None:
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        # Adjacency: source -> [(relation, target, properties)]
        self._adj: Dict[str, List[Edge]] = defaultdict(list)
        # Reverse adjacency: target -> [edge, ...]
        self._radj: Dict[str, List[Edge]] = defaultdict(list)
        # Indexes by type and by match key for teams.
        self._by_type: Dict[str, List[Node]] = defaultdict(list)
        self._team_by_key: Dict[str, str] = {}

    # -- node / edge mutation ------------------------------------------------

    def add_node(self, type_: str, id_: str, label: str, **properties) -> Node:
        """Add (or upsert) a node and return it."""
        node = Node(id=id_, type=type_, label=label, properties=properties)
        if id_ not in self.nodes:
            self.nodes[id_] = node
            self._by_type[type_].append(node)
            if type_ == "team":
                self._team_by_key[id_] = id_
        else:
            # Merge properties.
            self.nodes[id_].properties.update(properties)
        return self.nodes[id_]

    def add_edge(self, source: str, target: str, relation: str, **properties) -> Edge:
        """Add a directed edge *source* -> *target* with *relation*."""
        edge = Edge(source=source, target=target, relation=relation, properties=properties)
        self.edges.append(edge)
        self._adj[source].append(edge)
        self._radj[target].append(edge)
        return edge

    # -- lookups -------------------------------------------------------------

    def get_node(self, id_: str) -> Optional[Node]:
        return self.nodes.get(id_)

    def nodes_by_type(self, type_: str) -> List[Node]:
        return list(self._by_type.get(type_, []))

    def team_node_id(self, name: str) -> str:
        """Return the graph node id for a team name (accent/case-insensitive)."""
        return team_key(name)

    def team_label(self, name: str) -> str:
        """Return the preferred display label for a team name."""
        node = self.nodes.get(team_key(name))
        if node is not None:
            return node.label
        from .normalize import normalize_team

        return normalize_team(name)

    def find_team(self, query: str) -> Optional[Node]:
        """Find a team node by accent/case-insensitive substring match."""
        q = team_key(query)
        if not q:
            return None
        # Exact key match first.
        if q in self._team_by_key:
            return self.nodes[self._team_by_key[q]]
        # Substring match on the canonical key.
        matches = [n for n in self._by_type.get("team", []) if q in n.id]
        if not matches:
            # Try matching on the stripped label too.
            matches = [
                n for n in self._by_type.get("team", [])
                if q in n.label.lower() or q in n.id
            ]
        return matches[0] if matches else None

    def neighbors(self, source: str, relation: Optional[str] = None) -> List[Edge]:
        """Return outgoing edges from *source*, optionally filtered by relation."""
        edges = self._adj.get(source, [])
        if relation is None:
            return list(edges)
        return [e for e in edges if e.relation == relation]

    def incoming(self, target: str, relation: Optional[str] = None) -> List[Edge]:
        """Return incoming edges to *target*, optionally filtered by relation."""
        edges = self._radj.get(target, [])
        if relation is None:
            return list(edges)
        return [e for e in edges if e.relation == relation]

    def relations_of(self, source_id: str, relation: str) -> List[Node]:
        """Return the nodes that *source_id* connects to via *relation*."""
        return [self.nodes[e.target] for e in self._adj.get(source_id, []) if e.relation == relation]

    # -- summary -------------------------------------------------------------

    def summary(self) -> Dict[str, int]:
        """Return counts of nodes/edges by type/relation."""
        counts: Dict[str, int] = defaultdict(int)
        for n in self.nodes.values():
            counts[f"nodes/{n.type}"] += 1
        for e in self.edges:
            counts[f"edges/{e.relation}"] += 1
        counts["edges/total"] = len(self.edges)
        return dict(counts)
