"""Shared fixtures: session-scoped dataset and query engine."""

import pytest

from brazilian_soccer_mcp import Dataset, QueryEngine


@pytest.fixture(scope="session")
def dataset() -> Dataset:
    return Dataset()


@pytest.fixture(scope="session")
def engine(dataset: Dataset) -> QueryEngine:
    return QueryEngine(dataset)
