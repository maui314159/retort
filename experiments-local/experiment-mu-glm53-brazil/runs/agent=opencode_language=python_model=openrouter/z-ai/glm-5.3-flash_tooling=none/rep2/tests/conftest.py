"""Shared pytest fixtures for the Brazilian Soccer MCP test suite.

The real Kaggle datasets are loaded once per test session (about three
seconds) and shared by every BDD scenario and unit test.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from pytest_bdd import given

from brazilian_soccer_mcp.data_loader import SoccerData
from brazilian_soccer_mcp.knowledge_graph import KnowledgeGraph
from brazilian_soccer_mcp.queries import QueryEngine
from tests.steps.helpers import World

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"


@pytest.fixture(scope="session")
def data() -> SoccerData:
    return SoccerData(DATA_DIR)


@pytest.fixture(scope="session")
def engine(data: SoccerData) -> QueryEngine:
    return QueryEngine(data=data)


@pytest.fixture(scope="session")
def graph(data: SoccerData) -> KnowledgeGraph:
    return KnowledgeGraph(data)


@given("the Brazilian soccer data is loaded", target_fixture="world")
def world_loaded(engine) -> World:
    return World(engine)
