"""Shared pytest fixtures and BDD step glue.

A session-scoped :func:`data` fixture loads the datasets once for the whole
test run.  The ``Given the match data is loaded`` step seeds a fresh
per-scenario ``ctx`` dict that When/Then steps mutate to pass results.
"""

from __future__ import annotations

import pytest
from pytest_bdd import given

from brazilian_soccer.data_loader import get_data


@pytest.fixture(scope="session")
def data():
    """Loaded :class:`~brazilian_soccer.data_loader.Data` (shared)."""
    return get_data()


@given("the match data is loaded", target_fixture="ctx")
def match_data_loaded():
    """Seed a fresh per-scenario context dict.

    The session-scoped ``data`` fixture is requested on demand by the
    When/Then steps; this step only ensures ``ctx`` exists.
    """
    return {}
