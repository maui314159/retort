"""Shared pytest fixtures: one knowledge base per test session."""

from __future__ import annotations

import pytest

from soccer_mcp import SoccerDataService, load_knowledge_base

DATA_DIR = "data/kaggle"


@pytest.fixture(scope="session")
def kb():
    """Loaded knowledge base (all six CSVs) - shared across the session."""
    return load_knowledge_base(DATA_DIR)


@pytest.fixture(scope="session")
def svc(kb) -> SoccerDataService:
    """Query service over the shared knowledge base."""
    return SoccerDataService(kb)


@pytest.fixture(scope="session")
def registry(kb):
    return kb.registry


@pytest.fixture(scope="session")
def matches(kb):
    return kb.matches


@pytest.fixture(scope="session")
def players(kb):
    return kb.players


@pytest.fixture
def anyio_backend():
    return "asyncio"
