"""Shared pytest-bdd fixtures and steps for the Brazilian Soccer MCP suite."""

from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, when

import query_engine as qe
from soccer_data import get_store


@pytest.fixture(scope="session")
def store():
    """Session-scoped data store (loads the six CSV files once)."""
    return get_store()


@pytest.fixture
def context():
    """Scenario-scoped dict used to pass results between steps."""
    return {}


@given("the match data is loaded")
def match_data_loaded(store, context):
    context["store"] = store
    assert len(store.played_matches) > 0


@given("the player data is loaded")
def player_data_loaded(store, context):
    context["store"] = store
    assert len(store.players) > 0


@given("the soccer data is loaded")
def soccer_data_loaded(store, context):
    context["store"] = store


# Shared across player_queries.feature and normalization.feature.
@when(parsers.parse('I search for players at club "{club}"'))
def search_players_by_club(store, context, club):
    context["result"] = qe.search_players(club=club, limit=100, store=store)
