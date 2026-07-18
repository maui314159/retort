"""
tests.conftest
==============

Shared pytest fixtures for BDD tests.

Context
-------
This conftest loads all datasets once per session (loading ~17 000 matches +
18 000 players takes ~4 s) and shares the :class:`QueryEngine` across all
test functions. BDD ``Given``/``When``/``Then`` steps store intermediate state
in a per-scenario ``state`` dict.
"""

from __future__ import annotations

import pytest
from pytest_bdd import given, when, then, parsers

from brazilian_soccer_mcp.data_loader import load_datasets
from brazilian_soccer_mcp.knowledge_graph import KnowledgeGraph
from brazilian_soccer_mcp.query_engine import QueryEngine


# ---------------------------------------------------------------------------
# Session-scoped engine (loaded once)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def engine() -> QueryEngine:
    """Build the query engine once for the whole test session."""
    data = load_datasets()
    graph = KnowledgeGraph(data)
    return QueryEngine(graph)


# ---------------------------------------------------------------------------
# Per-scenario state
# ---------------------------------------------------------------------------

@pytest.fixture
def state():
    """Per-scenario mutable dict for BDD steps."""
    return {}


# ---------------------------------------------------------------------------
# Shared Given steps
# ---------------------------------------------------------------------------

@given("the match data is loaded", target_fixture="state")
def match_data_loaded(state, engine):
    state["engine"] = engine
    return state


@given("the player data is loaded", target_fixture="state")
def player_data_loaded(state, engine):
    state["engine"] = engine
    return state


# ---------------------------------------------------------------------------
# Shared Then steps
# ---------------------------------------------------------------------------

@then("I should receive a list of matches")
def should_receive_match_list(state):
    result = state["result"]
    assert "match" in result.lower() or "found" in result.lower(), (
        f"Expected match list, got: {result[:200]}"
    )


@then("I should receive matches")
def should_receive_matches(state):
    result = state["result"]
    assert "match" in result.lower() or "found" in result.lower(), (
        f"Expected matches, got: {result[:200]}"
    )


@then("I should receive an error message")
def should_receive_error(state):
    result = state["result"]
    assert "not found" in result.lower() or "no " in result.lower(), (
        f"Expected error message, got: {result[:200]}"
    )
