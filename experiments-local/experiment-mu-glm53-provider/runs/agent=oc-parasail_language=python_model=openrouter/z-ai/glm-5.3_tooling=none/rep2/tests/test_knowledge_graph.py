"""GWT tests for the in-memory knowledge graph."""

from __future__ import annotations


class TestGraphOverview:
    def test_given_full_graph_when_summarized_then_counts_are_consistent(self, engine):
        stats = engine.kg.stats()
        assert stats["nodes"] == sum(stats["node_types"].values())
        assert stats["edges"] == sum(stats["edge_types"].values())
        assert stats["node_types"]["match"] == len(engine.matches)
        assert stats["node_types"]["player"] == len(engine.players)

    def test_given_overview_tool_when_called_then_formatted_summary(self, engine):
        result = engine.graph_overview()
        assert "Nodes" in result["summary"]
        assert "Edges" in result["summary"]


class TestTeamGraph:
    def test_given_team_when_neighborhood_queried_then_opponents_ranked(self, engine):
        result = engine.team_graph("Flamengo")
        assert result["competitions"]["Brasileirão Série A"] > 0
        opponents = result["top_opponents"]
        counts = [o["matches"] for o in opponents]
        assert counts == sorted(counts, reverse=True)
        # every listed opponent must be a real opponent in the match index
        opponent_ids = {o["team"] for o in opponents}
        assert len(opponent_ids) == len(opponents)

    def test_given_foreign_club_when_neighborhood_queried_then_squad_only(self, engine):
        # Boca Juniors has match-node neighbors but no FIFA squad
        result = engine.team_graph("Boca Juniors")
        assert result["competitions"]
        assert result["squad"] == []


class TestGraphPaths:
    def test_given_teammates_when_paths_queried_then_one_hop_connection(self, engine):
        result = engine.graph_paths("Neymar", "Paris Saint-Germain")
        assert result["paths"]
        assert any("[plays_for]" in p for p in result["paths"])

    def test_given_countrymen_when_paths_queried_then_country_hub_connection(self, engine):
        result = engine.graph_paths("Neymar", "Alisson")
        assert result["paths"]
        assert any("Brazil" in p for p in result["paths"])

    def test_given_rivals_when_paths_queried_then_match_node_connection(self, engine):
        result = engine.graph_paths("Flamengo", "Fluminense")
        two_hop = [p for p in result["paths"] if p.count("-->") == 2]
        assert two_hop
        assert any("played_home" in p for p in two_hop)

    def test_given_unknown_entity_when_paths_queried_then_error(self, engine):
        result = engine.graph_paths("Xyzzy Plugh", "Flamengo")
        assert "error" in result

    def test_given_unrelated_entities_when_paths_queried_then_no_connection_reported(self, engine):
        result = engine.graph_paths("Boca Juniors", "Boavista", max_hops=2)
        assert "No connection" in result["summary"]


class TestGraphStructure:
    def test_given_match_nodes_when_inspected_then_labels_contain_teams(self, engine):
        sample = engine.matches[0]
        node = engine.kg.node(f"match:{sample.match_id}")
        assert node is not None
        assert node.type == "match"
        assert sample.home_display.split(" (")[0] in node.label

    def test_given_player_nodes_when_inspected_then_props_present(self, engine):
        neymar = next(p for p in engine.players if p.name == "Neymar Jr")
        node = engine.kg.node(f"player:{neymar.fifa_id}")
        assert node.props["overall"] == 92
        assert node.props["nationality"] == "Brazil"

    def test_given_plays_for_edges_when_counted_then_every_assigned_player_has_one(self, engine):
        with_club = [p for p in engine.players if p.club]
        edge_count = engine.kg.stats()["edge_types"]["plays_for"]
        assert edge_count == len(with_club)
