"""In-memory property knowledge graph over the soccer datasets.

Nodes (``type:id``):
    club:<club_id>          a team (Brazilian or foreign fallback identity)
    player:<fifa_id>        a player from the FIFA dataset
    match:<match_id>        a played/scheduled fixture
    competition:<family>    a competition (Série A, Copa do Brasil, ...)

Edges (typed, undirected traversal):
    played_home    (match) -> (club)
    played_away    (match) -> (club)
    won            (match) -> (club)         [only when a winner exists]
    part_of        (match) -> (competition)
    plays_for      (player) -> (club)         [FIFA snapshot]
    from_country   (player) -> (country:<name>)

The graph answers structural questions the relational queries cannot express
directly: "which competitions has Palmeiras played in" (two hops through
match nodes), "who are Neymar's teammates", "how do two entities connect".
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field

from .models import Match, Player


@dataclass
class _Node:
    id: str
    type: str
    label: str
    props: dict = field(default_factory=dict)


class KnowledgeGraph:
    """Adjacency-list property graph with typed edges."""

    def __init__(self) -> None:
        self._nodes: dict[str, _Node] = {}
        self._adj: dict[str, list[tuple[str, str]]] = defaultdict(list)
        self._edge_counts: dict[str, int] = defaultdict(int)

    # -- construction ----------------------------------------------------
    def add_node(self, node_id: str, node_type: str, label: str, **props) -> str:
        if node_id not in self._nodes:
            self._nodes[node_id] = _Node(node_id, node_type, label, dict(props))
        return node_id

    def add_edge(self, src: str, dst: str, relation: str) -> None:
        if src not in self._nodes or dst not in self._nodes:
            return
        self._adj[src].append((relation, dst))
        self._adj[dst].append((f"~{relation}", src))
        self._edge_counts[relation] += 1

    # -- queries ----------------------------------------------------------
    def node(self, node_id: str) -> _Node | None:
        return self._nodes.get(node_id)

    def node_ids(self, node_type: str | None = None) -> list[str]:
        if node_type is None:
            return list(self._nodes)
        return [n.id for n in self._nodes.values() if n.type == node_type]

    def neighbors(self, node_id: str, relation: str | None = None) -> list[tuple[str, _Node]]:
        """Direct neighbors as (relation, node); relation '~r' marks reverse."""
        result = []
        for rel, other in self._adj.get(node_id, ()):
            if relation is None or rel in (relation, f"~{relation}"):
                result.append((rel, self._nodes[other]))
        return result

    def degree(self, node_id: str) -> int:
        return len(self._adj.get(node_id, ()))

    def find_node(self, label_query: str) -> list[_Node]:
        """Case-insensitive substring search over node labels."""
        q = label_query.lower()
        return [n for n in self._nodes.values() if q in n.label.lower()]

    def stats(self) -> dict:
        type_counts: dict[str, int] = defaultdict(int)
        for n in self._nodes.values():
            type_counts[n.type] += 1
        return {
            "nodes": len(self._nodes),
            "node_types": dict(type_counts),
            "edges": sum(self._edge_counts.values()),
            "edge_types": dict(self._edge_counts),
        }

    def find_paths(self, start: str, goal: str, max_hops: int = 3, max_frontier: int = 250) -> list[list[tuple[str, str]]]:
        """BFS paths between two nodes as lists of (relation, node_id) steps.

        The number of returned paths is capped to keep responses bounded.
        """
        if start == goal:
            return [[]]
        paths: list[list[tuple[str, str]]] = []
        queue: deque[tuple[str, list[tuple[str, str]]]] = deque([(start, [])])
        visited_best: dict[str, int] = {start: 0}
        while queue and len(paths) < 10:
            current, trail = queue.popleft()
            if len(trail) >= max_hops:
                continue
            frontier = 0
            for rel, other in self._adj.get(current, ()):
                frontier += 1
                if frontier > max_frontier:
                    break
                step = trail + [(rel, other)]
                if other == goal:
                    paths.append(step)
                    continue
                hops = len(step)
                if visited_best.get(other, 99) <= hops:
                    continue
                visited_best[other] = hops
                queue.append((other, step))
        return paths

    def as_dict(self) -> dict:
        return self.stats()


def build_knowledge_graph(
    matches: list[Match],
    players: list[Player],
    club_registry: dict,
    display_for: dict[str, str],
    fifa_club_map: dict[str, str],
) -> KnowledgeGraph:
    """Build the full knowledge graph from matches and players.

    ``club_registry`` maps club_id -> Club (curated + fallback identities),
    ``display_for`` maps club_id -> display name used on match rows, and
    ``fifa_club_map`` maps raw FIFA club strings (e.g. "Paris
    Saint-Germain") to club ids so every player gets a plays_for edge.
    """
    kg = KnowledgeGraph()

    competitions_seen: dict[str, str] = {}
    for m in matches:
        competitions_seen.setdefault(m.family, m.competition)
    for family, display in competitions_seen.items():
        kg.add_node(f"competition:{family}", "competition", display)

    for club_id, club in club_registry.items():
        kg.add_node(
            f"club:{club_id}",
            "club",
            display_for.get(club_id, club.display),
            state=club.state,
            country=club.country,
        )

    for m in matches:
        mid = f"match:{m.match_id}"
        label = f"{m.home_display} vs {m.away_display}"
        if m.played:
            label += f" {m.home_goals}-{m.away_goals}"
        if m.date:
            label = f"{m.date.isoformat()} " + label
        kg.add_node(mid, "match", label, competition=m.family, season=m.season)
        kg.add_edge(mid, f"club:{m.home_team}", "played_home")
        kg.add_edge(mid, f"club:{m.away_team}", "played_away")
        kg.add_edge(mid, f"competition:{m.family}", "part_of")
        if m.winner():
            kg.add_edge(mid, f"club:{m.winner()}", "won")

    for p in players:
        pid = f"player:{p.fifa_id}"
        kg.add_node(
            pid,
            "player",
            p.name,
            nationality=p.nationality,
            overall=p.overall,
            position=p.position,
        )
        club_id = fifa_club_map.get(p.club or "", p.club_id)
        if club_id:
            kg.add_edge(pid, f"club:{club_id}", "plays_for")
        kg.add_node(f"country:{p.nationality}", "country", p.nationality)
        kg.add_edge(pid, f"country:{p.nationality}", "from_country")

    return kg
