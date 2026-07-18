"""Shared pytest fixtures for the Brazilian Soccer MCP test suite."""
from __future__ import annotations

import pytest


@pytest.fixture(scope="session")
def matches_df():
    """Load the full match DataFrame once per session (lru_cache shares)."""
    from brazilian_soccer.loader import load_matches
    return load_matches()


@pytest.fixture(scope="session")
def players_df():
    """Load the full player DataFrame once per session (lru_cache shares)."""
    from brazilian_soccer.loader import load_players
    return load_players()
