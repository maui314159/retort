"""In-memory knowledge graph for the Brazilian Soccer MCP Server.

Builds a lightweight property graph from the unified datasets:

* ``Team``     -- every club appearing in the match data
* ``Player``   -- every player in the FIFA database
* ``Club``     -- the (FIFA) club a player is registered at; linked to a
  ``Team`` node via ``SAME_AS`` when the club matches a match-data team
* ``Competition`` -- Brasileirão Série A/B/C, Copa do Brasil, Libertadores
* ``Match``    -- one node per de-duplicated fixture

Edge types::

    Team    --[PARTICIPATES_IN]--> Competition
    Team    --[PLAYED]--> Match          (props: role, goals)
    Team    --[BEAT|DREW_WITH|LOST_TO]--> Team   (props: match_id, score)
    Player  --[PLAYS_FOR]--> Club        (props: position, jersey)
    Club    --[SAME_AS]--> Team          (when club name resolves to a team)
    Match   --[IN_COMPETITION]--> Competition

The graph answers structural questions ("who played for club X", "which
teams competed in competition Y", "who beat whom") without SQL-style scans
and is exposed through the ``search_knowledge_graph`` and
``graph_neighbors`` MCP tools.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from .data_loader import Player, SoccerData
from .normalize import competition_key, key_team, normalize_key


def _fold(text: str) -> str:
    """Accent/case-insensitive lookup key for node names."""
    return normalize_key(text)


@dataclass
class Node:
    node_id: str
    type: str
    name: str
    props: dict = field(default_factory=dict)


@dataclass
class Edge:
    edge_id: str
    source: str  # node_id
    target: str  # node_id
    type: str
    props: dict = field(default_factory=dict)


class KnowledgeGraph:
    """Property graph over teams, players, clubs, competitions and matches."""

    def __init__(self, data: SoccerData, build: bool = True):
        self.nodes: dict[str, Node] = {}
        self.edges: dict[str, Edge] = {}
        self._adjacency: dict[str, list[tuple[str, Edge]]] = defaultdict(list)
        self._by_name: dict[str, list[str]] = defaultdict(list)
        if build:
            self.build(data)

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _add_node(self, node_id: str, node_type: str, name: str, **props) -> Node:
        node = Node(node_id, node_type, name, props)
        self.nodes[node_id] = node
        self._by_name[_fold(name)].append(node_id)
        return node

    def _add_edge(self, edge_id: str, source: str, target: str, edge_type: str, **props) -> Edge:
        edge = Edge(edge_id, source, target, edge_type, props)
        self.edges[edge_id] = edge
        self._adjacency[source].append((target, edge))
        self._adjacency[target].append((source, edge))
        return edge

    def build(self, data: SoccerData) -> None:
        """(Re)build every node and edge from ``data``."""
        self.nodes = {}
        self.edges = {}
        self._adjacency = defaultdict(list)
        self._by_name = defaultdict(list)

        for comp_name, count in data.competition_names().items():
            self._add_node(
                f"comp:{competition_key(comp_name)}",
                "Competition",
                comp_name,
                match_count=count,
            )

        team_ids: dict[str, str] = {}
        for name in data.team_names():
            node_id = f"team:{key_team(name)}"
            team_ids[key_team(name)] = node_id
            self._add_node(node_id, "Team", name)

        player_number = 0
        club_ids: dict[str, str] = {}
        for player in data.players:
            player_number += 1
            node_id = f"player:{player_number}"
            self._add_node(
                node_id,
                "Player",
                player.name,
                age=player.age,
                nationality=player.nationality,
                overall=player.overall,
                potential=player.potential,
                position=player.position,
            )
            if player.club:
                club_key = key_team(player.club)
                club_id = club_ids.get(club_key)
                if club_id is None:
                    club_id = f"club:{club_key}"
                    club_ids[club_key] = club_id
                    self._add_node(club_id, "Club", player.club)
                self._add_edge(
                    f"{node_id}|plays_for|{club_id}",
                    node_id,
                    club_id,
                    "PLAYS_FOR",
                    position=player.position,
                    jersey_number=player.jersey_number,
                )
                team_id = team_ids.get(club_key)
                if team_id is not None:
                    self._add_edge(f"{club_id}|same_as|{team_id}", club_id, team_id, "SAME_AS")

        for match in data.matches:
            match_id = f"match:{match.match_id}"
            self._add_node(
                match_id,
                "Match",
                match_label(match),
                date=match.date,
                season=match.season,
                round=match.round,
                stage=match.stage,
                home_team=match.home_team,
                away_team=match.away_team,
                home_goals=match.home_goals,
                away_goals=match.away_goals,
            )
            comp_id = f"comp:{match.competition_key}"
            if comp_id in self.nodes:
                self._add_edge(f"{match_id}|in_comp|{comp_id}", match_id, comp_id, "IN_COMPETITION")
            home_id = team_ids.get(key_team(match.home_team))
            away_id = team_ids.get(key_team(match.away_team))
            if home_id and away_id:
                for role, team_id in (("home", home_id), ("away", away_id)):
                    goals = match.home_goals if role == "home" else match.away_goals
                    self._add_edge(
                        f"{match_id}|played|{team_id}|{role}",
                        team_id,
                        match_id,
                        "PLAYED",
                        role=role,
                        goals=goals,
                    )
                winner = match.winner
                loser = None
                if winner == match.home_team:
                    loser_id, winner_id = away_id, home_id
                    loser = match.away_team
                elif winner == match.away_team:
                    loser_id, winner_id = home_id, away_id
                if winner:
                    score = f"{match.home_goals}-{match.away_goals}"
                    self._add_edge(
                        f"{match_id}|beat|{winner_id}",
                        winner_id,
                        loser_id or away_id,
                        "BEAT",
                        match_id=match.match_id,
                        score=score,
                    )
                    if loser_id:
                        self._add_edge(
                            f"{match_id}|lost|{loser_id}",
                            loser_id,
                            winner_id,
                            "LOST_TO",
                            match_id=match.match_id,
                            score=score,
                        )
                else:
                    score = f"{match.home_goals}-{match.away_goals}"
                    self._add_edge(
                        f"{match_id}|drew|{home_id}",
                        home_id,
                        away_id,
                        "DREW_WITH",
                        match_id=match.match_id,
                        score=score,
                    )
                    self._add_edge(
                        f"{match_id}|drew|{away_id}",
                        away_id,
                        home_id,
                        "DREW_WITH",
                        match_id=match.match_id,
                        score=score,
                    )

        # Competition participation from actual fixtures.
        for match in data.matches:
            comp_id = f"comp:{match.competition_key}"
            for team in (match.home_team, match.away_team):
                team_id = team_ids.get(key_team(team))
                if team_id and comp_id in self.nodes:
                    edge_id = f"{team_id}|participates|{comp_id}"
                    if edge_id not in self.edges:
                        self._add_edge(edge_id, team_id, comp_id, "PARTICIPATES_IN")

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def search_nodes(self, query: str, node_types: list[str] | None = None, limit: int = 20) -> list[Node]:
        """Substring search over node names, optionally filtered by type."""
        query = _fold(query)
        if not query:
            return []
        results: list[Node] = []
        for name_lower, ids in self._by_name.items():
            if query in name_lower:
                for node_id in ids:
                    node = self.nodes[node_id]
                    if node_types and node.type not in node_types:
                        continue
                    results.append(node)
        results.sort(key=lambda n: (n.name.lower().find(query), n.type, n.name))
        return results[:limit]

    def get_node(self, name: str, node_types: list[str] | None = None) -> Node | None:
        """Exact-ish node lookup by name (accent/case insensitive)."""
        target = _fold(name)
        if target in self._by_name:
            for node_id in self._by_name[target]:
                node = self.nodes[node_id]
                if not node_types or node.type in node_types:
                    return node
        matches = self.search_nodes(name, node_types, limit=1)
        return matches[0] if matches else None

    def neighbors(self, name: str, edge_types: list[str] | None = None, limit: int = 50,
                  node_types: list[str] | None = None) -> dict:
        """Return a node and its relationships grouped by edge type."""
        node = self.get_node(name, node_types)
        if node is None:
            return {}
        grouped: dict[str, list[dict]] = defaultdict(list)
        for other_id, edge in self._adjacency.get(node.node_id, []):
            if edge_types and edge.type not in edge_types:
                continue
            other = self.nodes[other_id]
            grouped[edge.type].append(
                {
                    "node": {"id": other.node_id, "type": other.type, "name": other.name},
                    "direction": "outgoing" if edge.source == node.node_id else "incoming",
                    "props": dict(edge.props),
                }
            )
        for entries in grouped.values():
            entries.sort(key=lambda item: item["node"]["name"].lower())
            del entries[limit:]
        return {
            "node": {"id": node.node_id, "type": node.type, "name": node.name, "props": node.props},
            "relationships": dict(sorted(grouped.items())),
        }

    def stats(self) -> dict:
        counts: dict[str, int] = defaultdict(int)
        for node in self.nodes.values():
            counts[node.type] += 1
        edge_counts: dict[str, int] = defaultdict(int)
        for edge in self.edges.values():
            edge_counts[edge.type] += 1
        return {"nodes": dict(sorted(counts.items())), "edges": dict(sorted(edge_counts.items()))}


def match_label(match) -> str:
    """Human-readable label for a match node, e.g. ``Flamengo 2-1 Fluminense``."""
    if match.home_goals is None or match.away_goals is None:
        return f"{match.home_team} vs {match.away_team}"
    return f"{match.home_team} {match.home_goals}-{match.away_goals} {match.away_team}"
