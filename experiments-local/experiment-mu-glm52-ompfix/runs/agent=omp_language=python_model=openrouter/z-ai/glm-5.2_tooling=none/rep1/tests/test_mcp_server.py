"""
tests.test_mcp_server
=====================

Direct (non-BDD) tests for the MCP server tools and core modules.

Covers:
  * Server tool registry (all tools registered and callable)
  * Each tool returns a non-empty string for real queries
  * Team-name normalizer (suffix stripping, accent folding, collision
    disambiguation)
  * Data loader (record counts, date parsing, cross-source dedup)
  * Knowledge graph (node/edge counts, index completeness)

These complement the BDD ``.feature`` tests with structural assertions.
"""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp import server
from brazilian_soccer_mcp.normalize import TeamNormalizer, make_key, _parse
from brazilian_soccer_mcp.data_loader import load_datasets
from brazilian_soccer_mcp.knowledge_graph import KnowledgeGraph
from brazilian_soccer_mcp.query_engine import QueryEngine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def loaded_data():
    return load_datasets()


@pytest.fixture(scope="session")
def graph(loaded_data):
    return KnowledgeGraph(loaded_data)


@pytest.fixture(scope="session")
def engine(graph):
    return QueryEngine(graph)


# ---------------------------------------------------------------------------
# Normalizer tests
# ---------------------------------------------------------------------------


class TestNormalizer:
    """Team-name normalisation unit tests."""

    def test_strips_state_suffix(self):
        nz = TeamNormalizer(["Palmeiras-SP", "Flamengo-RJ"])
        assert nz.canonical("Palmeiras-SP") == "Palmeiras"
        assert nz.canonical("Flamengo-RJ") == "Flamengo"

    def test_handles_spaces_around_dash(self):
        nz = TeamNormalizer(["América - MG"])
        assert nz.canonical("América - MG") == "América-MG"

    def test_accent_folding(self):
        assert make_key("São Paulo") == make_key("Sao Paulo")
        assert make_key("Grêmio") == make_key("Gremio")

    def test_collision_disambiguation_atletico(self):
        """Atlético-MG, Atletico-PR, Atlético-GO must stay distinct."""
        nz = TeamNormalizer(
            ["Atlético-MG", "Atletico-PR", "Atlético-GO", "Atlético - ES"]
        )
        assert nz.canonical("Atlético-MG") == "Atlético-MG"
        assert nz.canonical("Atletico-PR") == "Athletico-PR"
        assert nz.canonical("Atlético-GO") == "Atlético-GO"

    def test_bare_athletico_defaults_to_pr(self):
        nz = TeamNormalizer(["Athletico", "Athletico-PR"])
        assert nz.canonical("Athletico") == "Athletico-PR"

    def test_parse_strips_parentheticals(self):
        base, state = _parse("América FC (Minas Gerais)")
        assert "Minas Gerais" not in base
        assert state is None

    def test_parse_3_letter_country_code(self):
        base, state = _parse("Barcelona-EQU")
        assert state == "EQU"
        assert base == "Barcelona"


# ---------------------------------------------------------------------------
# Data loader tests
# ---------------------------------------------------------------------------


class TestDataLoader:
    """Verify all 6 CSV files are loaded with correct record counts."""

    def test_matches_loaded(self, loaded_data):
        assert len(loaded_data.matches) > 15000, (
            f"Expected >15000 matches, got {len(loaded_data.matches)}"
        )

    def test_players_loaded(self, loaded_data):
        assert len(loaded_data.players) == 18207, (
            f"Expected 18207 players, got {len(loaded_data.players)}"
        )

    def test_all_six_sources_present(self, loaded_data):
        sources = {m.source_file for m in loaded_data.matches}
        expected = {
            "Brasileirao_Matches.csv",
            "novo_campeonato_brasileiro.csv",
            "Brazilian_Cup_Matches.csv",
            "Libertadores_Matches.csv",
            "BR-Football-Dataset.csv",
        }
        assert expected.issubset(sources), f"Missing sources: {expected - sources}"

    def test_brasileirao_seasons_span_2003_to_2022(self, loaded_data):
        bra = [m for m in loaded_data.matches
               if m.competition == "Brasileirão Serie A" and m.season]
        seasons = {m.season for m in bra}
        assert min(seasons) <= 2003
        assert max(seasons) >= 2022

    def test_no_double_counting_2019_brasileirao(self, loaded_data):
        """2019 Serie A must not be double-counted (BR-Football dedup)."""
        bra_2019 = [
            m for m in loaded_data.matches
            if m.competition == "Brasileirão Serie A" and m.season == 2019
        ]
        # 20 teams * 38 rounds / 2 = 380 unique matches
        assert len(bra_2019) == 380, (
            f"Expected 380 unique 2019 matches, got {len(bra_2019)} (double-counted?)"
        )

    def test_dates_are_parsed(self, loaded_data):
        with_dates = [m for m in loaded_data.matches if m.date is not None]
        assert len(with_dates) > 10000

    def test_goals_are_integers(self, loaded_data):
        scored = [m for m in loaded_data.matches
                   if m.home_goals is not None and m.away_goals is not None]
        for m in scored[:100]:
            assert isinstance(m.home_goals, int)
            assert isinstance(m.away_goals, int)

    def test_novo_dates_brazilian_format(self, loaded_data):
        """novo (2003-2011) dates parsed from DD/MM/YYYY."""
        novo = [m for m in loaded_data.matches
                if m.source_file == "novo_campeonato_brasileiro.csv"]
        assert novo, "No novo matches loaded"
        for m in novo[:20]:
            assert m.date is not None, f"Date not parsed: {m.id}"


# ---------------------------------------------------------------------------
# Knowledge graph tests
# ---------------------------------------------------------------------------


class TestKnowledgeGraph:
    """Graph structure and index tests."""

    def test_nodes_created(self, graph):
        assert graph.node_count() > 500

    def test_edges_created(self, graph):
        assert graph.edge_count() > 30000

    def test_competitions_list(self, graph):
        comps = graph.competitions_list()
        assert "Brasileirão Serie A" in comps
        assert "Copa do Brasil" in comps
        assert "Copa Libertadores" in comps

    def test_team_index(self, graph):
        flamengo = graph.matches_for_team("Flamengo")
        assert len(flamengo) > 100, f"Expected >100 Flamengo matches, got {len(flamengo)}"

    def test_resolve_team_variations(self, graph):
        """All these spellings must resolve to the same canonical team."""
        for spelling in ("Flamengo", "Flamengo-RJ", "Flamengo - RJ"):
            assert graph.resolve_team(spelling) == "Flamengo", (
                f"{spelling!r} did not resolve to 'Flamengo'"
            )

    def test_resolve_team_atletico_disambiguation(self, graph):
        assert graph.resolve_team("Atlético-MG") == "Atlético-MG"
        assert graph.resolve_team("Atletico-PR") == "Athletico-PR"

    def test_head_to_head_index(self, graph):
        h2h = graph.head_to_head("Flamengo", "Fluminense")
        assert len(h2h) >= 20, f"Expected >=20 Fla-Flu matches, got {len(h2h)}"

    def test_players_by_nationality(self, graph):
        brazilians = graph.players_for_nationality("Brazil")
        assert len(brazilians) == 827, f"Expected 827 Brazilians, got {len(brazilians)}"


# ---------------------------------------------------------------------------
# Query engine tests
# ---------------------------------------------------------------------------


class TestQueryEngine:
    """Query engine output tests with real data."""

    def test_search_matches_returns_string(self, engine):
        r = engine.search_matches(team="Palmeiras", season=2023, limit=5)
        assert isinstance(r, str) and len(r) > 0

    def test_head_to_head_fla_flu(self, engine):
        r = engine.head_to_head("Flamengo", "Fluminense")
        assert "Flamengo" in r and "Fluminense" in r
        assert "wins" in r

    def test_team_statistics(self, engine):
        r = engine.team_statistics("Flamengo", season=2019)
        assert "Wins:" in r and "Draws:" in r and "Losses:" in r

    def test_standings_2019_champion(self, engine):
        r = engine.standings("Brasileirão", 2019, top_n=5)
        assert "Flamengo" in r
        assert "Champion" in r
        assert "90 pts" in r

    def test_top_brazilian_players(self, engine):
        r = engine.top_brazilian_players(limit=5)
        assert "Neymar" in r
        assert "92" in r

    def test_search_player_by_name(self, engine):
        r = engine.search_players(name="Neymar")
        assert "Neymar" in r

    def test_competition_info(self, engine):
        r = engine.competition_info("Libertadores")
        assert "Seasons:" in r
        assert "Total matches:" in r

    def test_average_goals(self, engine):
        r = engine.average_goals(competition="Brasileirão")
        assert "Average goals per match:" in r
        assert "Home win rate:" in r

    def test_biggest_wins(self, engine):
        r = engine.biggest_wins(limit=5)
        assert "Biggest victories" in r

    def test_best_records(self, engine):
        r = engine.best_records(competition="Brasileirão", season=2019, venue="home")
        assert "1." in r

    def test_team_not_found(self, engine):
        r = engine.team_statistics("Nonexistent Team")
        assert "not found" in r.lower()

    def test_competition_not_found(self, engine):
        r = engine.standings("Nonexistent League", 2019)
        assert "not found" in r.lower()

    def test_competitions_for_team(self, engine):
        r = engine.competitions_for_team("Palmeiras")
        assert "Brasileirão" in r
        assert "Libertadores" in r


# ---------------------------------------------------------------------------
# MCP server tool tests
# ---------------------------------------------------------------------------


class TestMCPServerTools:
    """Verify the FastMCP server exposes all required tools."""

    def test_server_has_tools(self):
        # FastMCP stores tools on the instance; access via the decorator registry
        # _tool_manager or the public list_tools API depending on version.
        tools = server.mcp._tool_manager.list_tools()
        tool_names = {t.name for t in tools}
        expected = {
            "search_matches", "head_to_head", "team_statistics",
            "compare_teams", "team_competitions", "search_players",
            "top_players_at_club", "top_brazilian_players",
            "standings", "competition_info", "average_goals",
            "biggest_wins", "best_records",
        }
        assert expected.issubset(tool_names), f"Missing tools: {expected - tool_names}"

    def test_each_tool_is_callable(self, engine):
        """Call each query-engine method backing a tool with real data."""
        assert engine.search_matches(team="Flamengo", limit=1)
        assert engine.head_to_head("Flamengo", "Fluminense")
        assert engine.team_statistics("Flamengo", season=2019)
        assert engine.compare_teams("Palmeiras", "Santos")
        assert engine.competitions_for_team("Palmeiras")
        assert engine.search_players(name="Neymar")
        assert engine.top_players_at_club("Fluminense")
        assert engine.top_brazilian_players(limit=1)
        assert engine.standings("Brasileirão", 2019, top_n=1)
        assert engine.competition_info("Libertadores")
        assert engine.average_goals(competition="Brasileirão")
        assert engine.biggest_wins(limit=1)
        assert engine.best_records(competition="Brasileirão", season=2019)


# ---------------------------------------------------------------------------
# Performance tests (spec: simple <2s, aggregate <5s)
# ---------------------------------------------------------------------------


class TestPerformance:
    """Query performance per the spec's success criteria."""

    def test_simple_lookup_under_2s(self, engine):
        import time
        start = time.time()
        engine.search_matches(team="Flamengo", season=2019, limit=10)
        elapsed = time.time() - start
        assert elapsed < 2.0, f"Simple lookup took {elapsed:.2f}s (>2s)"

    def test_aggregate_query_under_5s(self, engine):
        import time
        start = time.time()
        engine.standings("Brasileirão", 2019)
        elapsed = time.time() - start
        assert elapsed < 5.0, f"Aggregate query took {elapsed:.2f}s (>5s)"
