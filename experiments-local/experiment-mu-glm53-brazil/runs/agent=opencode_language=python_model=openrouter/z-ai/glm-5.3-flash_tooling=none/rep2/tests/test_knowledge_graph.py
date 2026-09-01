"""Unit tests for the in-memory knowledge graph."""

from __future__ import annotations

from brazilian_soccer_mcp.knowledge_graph import KnowledgeGraph


class TestGraphStructure:
    def test_node_types(self, graph: KnowledgeGraph) -> None:
        stats = graph.stats()
        for node_type in ("Team", "Player", "Club", "Competition", "Match"):
            assert node_type in stats["nodes"], node_type
        assert stats["nodes"]["Match"] > 10000
        assert stats["nodes"]["Player"] == 18207

    def test_edge_types(self, graph: KnowledgeGraph) -> None:
        edge_types = set(graph.stats()["edges"])
        assert {"PLAYED", "PARTICIPATES_IN", "PLAYS_FOR", "BEAT", "DREW_WITH",
                "IN_COMPETITION"} <= edge_types


class TestSearch:
    def test_search_teams(self, graph: KnowledgeGraph) -> None:
        nodes = graph.search_nodes("Palmeiras", node_types=["Team"], limit=10)
        assert nodes
        assert all(n.type == "Team" for n in nodes)
        assert any(n.name == "Palmeiras" for n in nodes)

    def test_search_players(self, graph: KnowledgeGraph) -> None:
        nodes = graph.search_nodes("Neymar", node_types=["Player"], limit=5)
        assert nodes
        assert nodes[0].props["overall"] == 92

    def test_search_matches(self, graph: KnowledgeGraph) -> None:
        nodes = graph.search_nodes("Flamengo 6-1 Goiás", node_types=["Match"], limit=5)
        assert nodes
        assert nodes[0].props["home_goals"] == 6

    def test_search_no_results(self, graph: KnowledgeGraph) -> None:
        assert graph.search_nodes("Zezinho Ninguem", limit=5) == []

    def test_get_node_accent_insensitive(self, graph: KnowledgeGraph) -> None:
        node = graph.get_node("sao paulo", node_types=["Team"])
        assert node is not None and node.name == "São Paulo"


class TestNeighbors:
    def test_team_neighbors(self, graph: KnowledgeGraph) -> None:
        result = graph.neighbors("Flamengo", limit=200)
        assert result["node"]["type"] == "Team"
        rel_types = set(result["relationships"])
        assert "PLAYED" in rel_types
        assert "PARTICIPATES_IN" in rel_types

    def test_player_plays_for(self, graph: KnowledgeGraph) -> None:
        result = graph.neighbors("Neymar Jr", edge_types=["PLAYS_FOR"])
        rels = result["relationships"].get("PLAYS_FOR", [])
        assert len(rels) == 1
        assert rels[0]["node"]["name"] == "Paris Saint-Germain"

    def test_unknown_node(self, graph: KnowledgeGraph) -> None:
        assert graph.neighbors("Zezinho Ninguem") == {}

    def test_club_same_as_team(self, graph: KnowledgeGraph) -> None:
        # FIFA "Grêmio" club should link to the match-data "Grêmio" team
        result = graph.neighbors("Grêmio", edge_types=["SAME_AS"], node_types=["Club"])
        rels = result["relationships"].get("SAME_AS", [])
        assert any(r["node"]["type"] == "Team" for r in rels)
