"""Shared pytest fixtures for the Brazilian Soccer MCP BDD test-suite.

Context
-------
Building the :class:`KnowledgeGraph` loads and deduplicates all six CSV
files (~17k matches + 18k players), which takes a couple of seconds.  We
build it **once per test session** and hand the same instance to every
BDD step, so the whole suite runs in well under the spec's per-query
budgets (simple lookups <2s, aggregates <5s).

The fixtures also stash the result of the most recent "When" step so the
Gherkin "Then" steps can assert on it without threading the value through
every step function signature.
"""

from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import given, when, then, parsers

from brazilian_soccer_mcp import build_server
from brazilian_soccer_mcp.knowledge_graph import KnowledgeGraph
from brazilian_soccer_mcp.loader import load_dataset
from brazilian_soccer_mcp import queries


@pytest.fixture(scope="session")
def dataset():
    """Load + dedup every CSV once for the whole session."""

    return load_dataset()


@pytest.fixture(scope="session")
def kg(dataset) -> KnowledgeGraph:
    """Session-shared knowledge graph over the loaded dataset."""

    return KnowledgeGraph(dataset)


@pytest.fixture(scope="session")
def server():
    """A FastMCP server instance (knowledge graph built lazily)."""

    return build_server()


@pytest.fixture
def context() -> dict[str, Any]:
    """Per-scenario scratchpad for the last action's result + parameters."""

    return {"result": None, "params": {}}
