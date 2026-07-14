"""
BDD step definitions for competition_queries.feature
"""

from __future__ import annotations

import json

from pytest_bdd import given, when, then, scenarios

scenarios("competition_queries.feature")


@given("the match data is loaded")
def match_data_loaded():
    pass


@when('I request standings for "Brasileirão" season 2019')
def standings_2019(invoker):
    invoker.result = json.loads(invoker.competition_standings(competition="Brasileirão", season=2019))


@then("I should receive a ranked table with points wins draws and losses")
def ranked_table(invoker):
    r = invoker.result
    assert isinstance(r, list)
    assert len(r) > 0
    # Verify structure
    for entry in r:
        assert "team" in entry
        assert "points" in entry
        assert "wins" in entry
        assert "draws" in entry
        assert "losses" in entry
    # Verify descending by points
    points = [e["points"] for e in r]
    assert points == sorted(points, reverse=True)
    # Verify first entry is champion-like
    assert r[0]["position"] == 1


@when("I list all competitions")
def list_comps(invoker):
    invoker.result = json.loads(invoker.list_competitions())


@then("I should see at least 3 different competitions")
def at_least_3_comps(invoker):
    assert len(invoker.result) >= 3


@when('I list seasons for "Brasileirão"')
def list_br_seasons(invoker):
    invoker.result = json.loads(invoker.list_seasons(competition="Brasileirão"))


@then("I should see multiple seasons")
def multiple_seasons(invoker):
    assert isinstance(invoker.result, list)
    assert len(invoker.result) > 1
