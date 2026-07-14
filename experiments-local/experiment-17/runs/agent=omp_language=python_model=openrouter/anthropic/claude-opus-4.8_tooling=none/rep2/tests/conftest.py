"""
Context
=======
Module: tests.conftest
Purpose: Shared pytest fixtures for the Brazilian Soccer MCP test suite.

The real bundled datasets are used (no mocks) so tests exercise the same data
path as production. The :class:`KnowledgeBase` is expensive to build (~0.4s, all
six CSVs) so it is constructed once per session and shared read-only.
"""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp import KnowledgeBase


@pytest.fixture(scope="session")
def kb() -> KnowledgeBase:
    """Session-scoped knowledge base loaded from the bundled Kaggle CSVs."""
    return KnowledgeBase()
