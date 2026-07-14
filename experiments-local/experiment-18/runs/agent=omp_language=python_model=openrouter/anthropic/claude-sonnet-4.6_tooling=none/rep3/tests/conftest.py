"""
================================================================================
tests.conftest
================================================================================
Context:
    Shared pytest fixtures for the Brazilian Soccer MCP test suite. The
    knowledge graph is expensive to build (~1.5s, ~24k matches + 18k players)
    so it is constructed once per test session and shared read-only across all
    scenarios.
================================================================================
"""

import pytest
from pytest_bdd import given

from brazil_soccer_mcp import build_graph


@pytest.fixture(scope="session")
def graph():
    return build_graph()


@pytest.fixture
def context():
    """Per-scenario mutable bag for Given/When/Then state."""
    return {}


@given("the match data is loaded")
def _match_data_loaded(graph):
    assert len(graph.matches) > 0


@given("the player data is loaded")
def _player_data_loaded(graph):
    assert len(graph.players) > 0
