"""Shared fixtures for the Brazilian Soccer test suite."""

from __future__ import annotations

import pytest

from soccer import load_soccer_data


@pytest.fixture(scope="session")
def data():
    """Given the match and player data is loaded."""
    return load_soccer_data()


@pytest.fixture(scope="session")
def server(data):
    """An MCP server wired to the loaded data."""
    from soccer.server import build_server

    return build_server(data)
