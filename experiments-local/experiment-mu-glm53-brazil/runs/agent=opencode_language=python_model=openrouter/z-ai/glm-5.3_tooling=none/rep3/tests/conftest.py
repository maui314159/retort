"""
Shared pytest fixtures for the Brazilian Soccer MCP test suite.

Context block
-------------
Why:
    Loading the six CSVs takes a couple of seconds; BDD scenarios across
    six test modules must share one ``Dataset`` instance (and its cached
    club registry) both for speed and for consistent expectations.

What:
    * ``dataset``     - module-scoped, loads the bundled Kaggle data once.
    * ``svc``         - the service module (pure functions over ``dataset``).
    * ``service``     - alias of ``svc`` for readable Given-steps.

Test:
    This file is fixtures-only; scenario suites live in
    ``tests/test_*.py`` and their Gherkin counterparts in
    ``tests/features/*.feature``.

Spec references:
    TASK.md "Testing Approach" (BDD / GWT structure) and "Success
    Criteria" -> "Query Performance" (fixtures enable the <2s / <5s
    assertions in ``tests/test_statistics.py``).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make the repository root importable regardless of where pytest runs from.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brazilian_soccer_mcp import service
from brazilian_soccer_mcp.dataset import Dataset, load_dataset


@pytest.fixture(scope="session")
def dataset() -> Dataset:
    """The assembled knowledge base, loaded once per test session."""
    return load_dataset(ROOT / "data" / "kaggle")


@pytest.fixture(scope="session")
def svc() -> object:
    """The service module (query API) for When-steps."""
    return service
