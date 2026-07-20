"""Shared pytest fixtures and Given steps for the BDD test suite."""

from __future__ import annotations

import pytest
from pytest_bdd import given

from brazilian_soccer_mcp import DataStore, QueryEngine


@pytest.fixture(scope="session")
def store() -> DataStore:
    return DataStore()


@pytest.fixture(scope="session")
def engine(store: DataStore) -> QueryEngine:
    return QueryEngine(store)


@pytest.fixture
def context() -> dict:
    """Scenario-scoped bag used to pass results between When/Then steps."""
    return {}


@given("the match data is loaded")
def match_data_loaded(engine: QueryEngine) -> None:
    assert not engine.store.matches.empty


@given("the player data is loaded")
def player_data_loaded(engine: QueryEngine) -> None:
    assert not engine.store.players.empty
