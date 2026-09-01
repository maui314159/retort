"""Shared pytest fixtures: one SoccerStore for the whole test session."""

from __future__ import annotations

import pytest

from brazilian_soccer.store import SoccerStore


@pytest.fixture(scope="session")
def store() -> SoccerStore:
    return SoccerStore()
