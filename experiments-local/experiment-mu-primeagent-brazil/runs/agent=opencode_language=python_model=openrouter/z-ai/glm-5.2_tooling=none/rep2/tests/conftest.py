"""Shared pytest fixtures for the Brazilian Soccer MCP test suite."""
from __future__ import annotations

import pytest

from brsl.knowledge_graph import KnowledgeGraph
from brsl.query_engine import QueryEngine
from brsl import data_loader as dl


@pytest.fixture(scope="session")
def matches_df() -> "object":
    return dl.load_matches()


@pytest.fixture(scope="session")
def deduped_df():
    return dl.load_matches_deduplicated()


@pytest.fixture(scope="session")
def players_df():
    return dl.load_players()


@pytest.fixture(scope="session")
def graph() -> KnowledgeGraph:
    return KnowledgeGraph.load()


@pytest.fixture(scope="session")
def engine(graph: KnowledgeGraph) -> QueryEngine:
    return QueryEngine(graph)
