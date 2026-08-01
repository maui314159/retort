"""Shared pytest fixtures and shared pytest-bdd step definitions.

The ``store`` fixture is session-scoped: the six CSVs are loaded and
normalized exactly once per test run (~1s), then shared by unit tests and
BDD scenarios. BDD steps live here so every feature-file test module can
use them (pytest-bdd discovers steps in conftest.py).
"""

from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, then, when

from soccer_mcp.data import DataStore


@pytest.fixture(scope="session")
def store() -> DataStore:
    return DataStore()


@pytest.fixture
def context() -> dict:
    """Mutable per-scenario bag used to pass data between BDD steps."""
    return {}


# ---------------------------------------------------------------------------
# Shared BDD steps
# ---------------------------------------------------------------------------

@given("the match data is loaded")
def match_data_loaded(store):
    assert len(store.matches) > 0


@given("the player data is loaded")
def player_data_loaded(store):
    assert len(store.players) > 0


@given("the soccer data store is loaded")
def data_store_loaded(store):
    assert len(store.matches) > 0 and len(store.players) > 0


@then(parsers.parse('the result should mention "{text}"'), converters={"text": str})
def result_should_mention(context, text):
    haystack = context.get("text", "")
    normalized = haystack.lower()
    assert text.lower() in normalized, f"{text!r} not found in:\n{haystack}"


@then("the result should not be empty")
def result_not_empty(context):
    assert context.get("result") is not None
    if "matches" in (context.get("result") or {}):
        assert context["result"]["matches"], "expected at least one match"
    if "players" in (context.get("result") or {}):
        assert context["result"]["players"], "expected at least one player"
