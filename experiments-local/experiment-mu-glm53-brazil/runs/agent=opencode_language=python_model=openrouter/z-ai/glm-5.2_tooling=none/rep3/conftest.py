"""Shared pytest fixtures for the Brazilian Soccer MCP test suite.

Context block
-------------
Purpose: Provide a single shared `SoccerData` fixture loaded once per
session so the BDD scenarios run fast (loading ~6 CSVs once, not per
test).

Why session scope: the data is read-only; loading all six files takes
~1s and there is no reason to repeat it across the ~30 test scenarios.
"""
from __future__ import annotations

import pytest

from data_loader import SoccerData, load_all


@pytest.fixture(scope="session")
def sd() -> SoccerData:
    return load_all()
