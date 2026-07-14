"""
Context
=======
Module: tests.conftest

Shared pytest fixtures for the BDD suite. The KnowledgeBase is expensive-ish
to build (reads six CSVs) but immutable, so it is session-scoped and shared
across every scenario. Individual scenarios accumulate their working values in
a fresh `context` dict (function-scoped) so steps in one scenario never leak
into another.

The data directory is resolved via the package's own auto-detection
(data_loader.default_data_dir), which already honours BR_SOCCER_DATA_DIR and
falls back to the repo's data/kaggle, so the tests run from anywhere.
"""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp.data_loader import build_knowledge_base


@pytest.fixture(scope="session")
def kb():
    """Session-wide, immutable KnowledgeBase shared by all scenarios."""
    return build_knowledge_base()


@pytest.fixture()
def context():
    """Per-scenario scratch space for Given/When/Then to pass values along."""
    return {}
