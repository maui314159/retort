"""Shared fixtures: load the datasets once for the whole test session."""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp import QueryEngine, SoccerDataset


@pytest.fixture(scope="session")
def dataset() -> SoccerDataset:
    return SoccerDataset()


@pytest.fixture(scope="session")
def engine(dataset: SoccerDataset) -> QueryEngine:
    return QueryEngine(dataset)


@pytest.fixture()
def context() -> dict:
    """Mutable per-scenario bag used by the BDD step definitions."""
    return {}
