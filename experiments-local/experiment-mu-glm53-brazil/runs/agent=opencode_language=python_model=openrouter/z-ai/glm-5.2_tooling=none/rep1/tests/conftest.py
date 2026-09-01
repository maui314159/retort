"""
Shared pytest fixtures for the Brazilian Soccer MCP test-suite.

Context block
=============
Purpose: provide a session-scoped, lazily-loaded :class:`SoccerQueryEngine`
so every BDD scenario reuses the same in-memory dataset (the ~24k matches /
18k players load in well under a second).
"""

from __future__ import annotations

import os
import sys

import pytest

# Ensure the package root is importable when running from the repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brazilian_soccer_mcp import SoccerQueryEngine


@pytest.fixture(scope="session")
def engine() -> SoccerQueryEngine:
    return SoccerQueryEngine()
