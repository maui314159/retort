"""
tests.test_match_queries
========================

BDD step definitions for ``features/match_queries.feature``.
"""

from __future__ import annotations

import pytest
from pytest_bdd import scenarios, when, then, parsers

scenarios("features/match_queries.feature")


@when('I search for matches between "Flamengo" and "Fluminense"', target_fixture="state")
def search_between_flamengo_fluminense(state):
    engine = state["engine"]
    # search_matches with both team and opponent gives matches between them
    state["result"] = engine.search_matches(team="Flamengo", opponent="Fluminense", limit=50)
    return state


@when('I request the head-to-head record between "Palmeiras" and "Santos"', target_fixture="state")
def h2h_palmeiras_santos(state):
    engine = state["engine"]
    state["result"] = engine.head_to_head("Palmeiras", "Santos")
    return state


@when(
    'I search for matches in competition "Brasileirão" in season 2019',
    target_fixture="state",
)
def search_brasileirao_2019(state):
    engine = state["engine"]
    state["result"] = engine.search_matches(competition="Brasileirão", season=2019, limit=10)
    return state


@when('I search for matches for team "Nonexistent FC"', target_fixture="state")
def search_nonexistent(state):
    engine = state["engine"]
    state["result"] = engine.search_matches(team="Nonexistent FC")
    return state


@then("each match should have date, scores, and competition")
def match_has_fields(state):
    result = state["result"]
    # at least one line with a date pattern and score
    assert any("- " in line and ": " in line for line in result.split("\n")), (
        f"Expected match lines with dates, got: {result[:200]}"
    )


@then("I should receive wins, losses, and draws for both teams")
def h2h_has_record(state):
    result = state["result"]
    assert "wins" in result, f"Expected wins in h2h result: {result[:200]}"
    assert "draws" in result, f"Expected draws in h2h result: {result[:200]}"


@then("I should receive matches from that competition and season")
def matches_from_comp_season(state):
    result = state["result"]
    assert "Brasileirão" in result, f"Expected Brasileirão in result: {result[:200]}"
