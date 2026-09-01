"""
Shared fixtures for the Brazilian Soccer MCP test suite.

The dataset (≈33k CSV rows) loads in under a second, but a session-scoped
fixture keeps every scenario running against one in-memory graph.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure the repository root is importable when pytest runs from anywhere.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brazilian_soccer_mcp import Dataset, load_dataset


@pytest.fixture(scope="session")
def ds() -> Dataset:
    """The whole knowledge graph, loaded once per test session."""
    return load_dataset()


@pytest.fixture(scope="session")
def ds_timed() -> tuple[Dataset, float]:
    """Dataset plus its load time in seconds (performance scenarios)."""
    import time

    started = time.perf_counter()
    dataset = load_dataset()
    return dataset, time.perf_counter() - started
