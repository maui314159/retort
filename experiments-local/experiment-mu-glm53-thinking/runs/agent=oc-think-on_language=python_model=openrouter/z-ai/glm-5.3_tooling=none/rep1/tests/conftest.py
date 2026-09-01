"""Shared fixtures for the Brazilian soccer test suite."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from brazilian_soccer.data import SoccerData


@pytest.fixture(scope="session")
def soccer() -> SoccerData:
    """Given the full match and player data is loaded (once per session)."""
    return SoccerData(REPO_ROOT / "data" / "kaggle")
