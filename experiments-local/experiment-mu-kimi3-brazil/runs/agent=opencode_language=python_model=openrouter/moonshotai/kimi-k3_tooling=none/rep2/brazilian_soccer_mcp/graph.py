"""Lightweight in-memory knowledge graph over the loaded datasets.

Nodes are teams, players, competitions and matches; edges capture the
relationships between them (``PLAYED_HOME``, ``PLAYED_AWAY``, ``PART_OF``,
``PLAYS_FOR``, ``HAS_NATIONALITY``).  The graph is intentionally
dependency-free (plain dict adjacency lists) and is used to answer
relationship-style questions such as "which competitions has Palmeiras played
in?" or "which players play for Flamengo?".
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterator

# Edge relation labels.
PLAYED_HOME = "PLAYED_HOME"
PLAYED_AWAY = "PLAYED_AWAY"
PART_OF = "PART_OF"
PLAYS_FOR = "PLAYS_FOR"
HAS_NATIONALITY = "HAS_NATIONALITY"


class KnowledgeGraph:
    """Adjacency-list graph: node id -> {relation -> set of node ids}."""

    def __init__(self, store) -> None:
        self._store = store
        self.edges: dict[str, dict[str, set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )
        self._build()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def add_edge(self, src: str, relation: str, dst: str) -> None:
        self.edges[src][relation].add(dst)
        # Reverse edge for cheap bidirectional traversal.
        self.edges[dst][f"_{relation}"].add(src)

    def _build(self) -> None:
        matches = self._store.matches
        for row in matches.itertuples(index=False):
            match_id = (
                f"match:{row.date}|{row.home_key}|{row.away_key}|{row.competition}"
            )
            self.add_edge(match_id, PLAYED_HOME, f"team:{row.home_key}")
            self.add_edge(match_id, PLAYED_AWAY, f"team:{row.away_key}")
            self.add_edge(match_id, PART_OF, f"competition:{row.competition}")

        players = self._store.players
        if not players.empty:
            cols = ["ID", "_club_key", "_nat_key"]
            for pid, club, nat in players[cols].itertuples(index=False, name=None):
                player_id = f"player:{pid}"
                if club:
                    self.add_edge(player_id, PLAYS_FOR, f"club:{club}")
                if nat:
                    self.add_edge(player_id, HAS_NATIONALITY, f"country:{nat}")

    # ------------------------------------------------------------------
    # Traversal helpers
    # ------------------------------------------------------------------

    def neighbors(self, node: str, relation: str) -> set[str]:
        return set(self.edges.get(node, {}).get(relation, set()))

    def team_competitions(self, team: str) -> list[str]:
        """Canonical competition labels in which *team* appears."""
        from .normalization import team_key

        key = team_key(team)
        node = f"team:{key}"
        competitions: set[str] = set()
        for relation in (f"_{PLAYED_HOME}", f"_{PLAYED_AWAY}"):
            for match_node in self.neighbors(node, relation):
                for comp_node in self.neighbors(match_node, PART_OF):
                    competitions.add(comp_node.split(":", 1)[1])
        return sorted(competitions)

    def team_opponents(self, team: str) -> set[str]:
        """Canonical keys of every opponent *team* has faced."""
        from .normalization import team_key

        key = team_key(team)
        node = f"team:{key}"
        opponents: set[str] = set()
        for own_rel, opp_rel in (
            (f"_{PLAYED_HOME}", PLAYED_AWAY),
            (f"_{PLAYED_AWAY}", PLAYED_HOME),
        ):
            for match_node in self.neighbors(node, own_rel):
                for opp_node in self.neighbors(match_node, opp_rel):
                    opponents.add(opp_node.split(":", 1)[1])
        return opponents

    def club_players(self, club: str) -> list[int]:
        """FIFA player IDs whose club name contains *club* (normalized)."""
        from .normalization import norm_text

        needle = norm_text(club)
        if not needle:
            return []
        club_node = f"club:{needle}"
        ids = [
            int(p.split(":", 1)[1])
            for p in self.neighbors(club_node, f"_{PLAYS_FOR}")
            if p.split(":", 1)[1].isdigit()
        ]
        if ids:
            return ids
        # Substring fallback across all club nodes.
        result: list[int] = []
        for node in self.iter_nodes(prefix="club:"):
            if needle in node:
                result.extend(
                    int(p.split(":", 1)[1])
                    for p in self.neighbors(node, f"_{PLAYS_FOR}")
                    if p.split(":", 1)[1].isdigit()
                )
        return sorted(set(result))

    def iter_nodes(self, prefix: str = "") -> Iterator[str]:
        for node in self.edges:
            if node.startswith(prefix):
                yield node

    def stats(self) -> dict:
        teams = sum(1 for _ in self.iter_nodes("team:"))
        players = sum(1 for _ in self.iter_nodes("player:"))
        comps = sum(1 for _ in self.iter_nodes("competition:"))
        matches = sum(1 for _ in self.iter_nodes("match:"))
        edge_count = sum(
            len(targets) for rels in self.edges.values() for targets in rels.values()
        )
        return {
            "teams": teams,
            "players": players,
            "competitions": comps,
            "matches": matches,
            "edges": edge_count,
        }
