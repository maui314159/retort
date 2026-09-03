"""
Context Block
=============

Module: tests.conftest
Purpose: Shared pytest fixtures for the Brazilian Soccer MCP test
         suite.  The data loader, knowledge graph, and query engine
         are loaded once per session and shared across all test
         modules to keep test execution fast (the spec requires
         simple lookups < 2 s and aggregates < 5 s).
"""

from __future__ import annotations

import sys
import os
from pathlib import Path

import pytest

# Ensure the src package is importable even without installation
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from brazilian_soccer_mcp.data_loader import DataLoader
from brazilian_soccer_mcp.knowledge_graph import KnowledgeGraph
from brazilian_soccer_mcp.queries import SoccerQueries


# ---------------------------------------------------------------------------
# Session-scoped fixtures (loaded once, reused everywhere)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def data_dir() -> str:
    """Return the path to the Kaggle data directory."""
    return str(PROJECT_ROOT / "data" / "kaggle")


@pytest.fixture(scope="session")
def loader(data_dir: str) -> DataLoader:
    """Load all CSV datasets once per session."""
    return DataLoader(data_dir=data_dir).load()


@pytest.fixture(scope="session")
def graph(loader: DataLoader) -> KnowledgeGraph:
    """Build the knowledge graph once per session."""
    return KnowledgeGraph(loader)


@pytest.fixture(scope="session")
def queries(graph: KnowledgeGraph) -> SoccerQueries:
    """Create the query engine once per session."""
    return SoccerQueries(graph)
