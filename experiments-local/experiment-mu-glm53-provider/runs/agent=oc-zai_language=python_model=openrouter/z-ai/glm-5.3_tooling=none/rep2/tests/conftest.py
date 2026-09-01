"""Shared fixtures for the BDD test suite."""

from __future__ import annotations

import pytest

from brazilian_soccer.data import load_dataset


@pytest.fixture(scope="session")
def dataset():
    """Given: the full dataset is loaded from data/kaggle."""
    return load_dataset()
