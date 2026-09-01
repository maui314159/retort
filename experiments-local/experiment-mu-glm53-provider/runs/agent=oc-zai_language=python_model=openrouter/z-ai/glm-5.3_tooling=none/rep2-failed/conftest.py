"""Shared pytest fixtures for the Brazilian Soccer MCP test suite.

BDD GWT background: the match and player data is loaded once per test
session (loading takes ~2 seconds because of the two-phase alias-learning
load), so every scenario reuses the same :class:`~data_loader.SoccerData`
instance via the ``data`` fixture.
"""

from __future__ import annotations

import pytest

from data_loader import SoccerData, get_data


@pytest.fixture(scope="session")
def data() -> SoccerData:
    """Given: the full dataset is loaded and deduplicated."""
    return get_data()
