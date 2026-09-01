"""Shared BDD fixtures: the knowledge graph is loaded once per session."""

from __future__ import annotations

import pytest

from brazilian_soccer import SoccerData, SoccerService


@pytest.fixture(scope="session")
def dataset() -> SoccerData:
    return SoccerData()


@pytest.fixture(scope="session")
def svc(dataset) -> SoccerService:
    return SoccerService(dataset)
