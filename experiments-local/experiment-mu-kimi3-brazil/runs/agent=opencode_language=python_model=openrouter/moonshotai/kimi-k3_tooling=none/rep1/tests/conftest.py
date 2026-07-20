"""Shared fixtures: one KnowledgeBase per test session (load takes < 1s)."""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp.data import KnowledgeBase, default_data_dir, load_kb


@pytest.fixture(scope="session")
def kb() -> KnowledgeBase:
    return load_kb(default_data_dir())
