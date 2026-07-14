# ============================================================================
# Context: Brazilian Soccer MCP Server benchmark.
# Shared pytest fixtures. Provides a single shared DataLoader (cached for the
# whole session) and a QueryEngine built on top of it, plus a built FastMCP
# server for tool-level tests.
# ----------------------------------------------------------------------------
from __future__ import annotations

import os
import sys

import pytest
from pytest_bdd import given, when, then, parsers

# Ensure the package root is importable when running from the repo dir.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brazilian_soccer_mcp import DataLoader, QueryEngine, build_server


@pytest.fixture(scope="session")
def loader() -> DataLoader:
    return DataLoader()


@pytest.fixture(scope="session")
def engine(loader) -> QueryEngine:
    return QueryEngine(loader)


@pytest.fixture(scope="session")
def server(engine):
    return build_server(engine.loader)


# ----------------------------------------------------------------------------
# Shared result containers
# ----------------------------------------------------------------------------
@pytest.fixture
def results():
    return {}


# ----------------------------------------------------------------------------
# Generic Given steps
# ----------------------------------------------------------------------------
@given("the match data is loaded", target_fixture="loaded_matches")
def loaded_matches(engine):
    assert len(engine.loader.matches) > 0, "Match data should be loaded"
    return engine


@given("the FIFA player data is loaded", target_fixture="loaded_players")
def loaded_players(engine):
    assert not engine.loader.players_df.empty, "Player data should be loaded"
    return engine
