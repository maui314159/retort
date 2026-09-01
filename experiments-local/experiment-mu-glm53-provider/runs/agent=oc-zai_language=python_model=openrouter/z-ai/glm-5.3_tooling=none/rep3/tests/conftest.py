"""
tests/conftest.py -- shared fixtures for the BDD test suite.

CONTEXT
-------
The Brazilian Soccer MCP test suite uses BDD Given/When/Then scenarios
(``soccer_mcp.bdd``) over the real datasets in data/kaggle/.  Loading all six
CSVs takes ~1s, so the dataset is a session-scoped fixture shared by every
test; the MCP server tests reuse the same in-process tool functions.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from soccer_mcp.data_loader import load_dataset  # noqa: E402


@pytest.fixture(scope="session")
def dataset():
    """All six CSVs, loaded and normalized once per test session."""
    return load_dataset(REPO_ROOT / "data" / "kaggle")


@pytest.fixture(scope="session")
def mcp_server():
    """A fully registered MCPServer (not yet running) for in-memory tests."""
    from server import build_server

    return build_server()
