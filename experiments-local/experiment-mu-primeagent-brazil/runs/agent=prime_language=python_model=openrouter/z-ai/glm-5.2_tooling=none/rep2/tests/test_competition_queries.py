"""
Context block
=============
Brazilian Soccer MCP Server - BDD Step Definitions: Competition Queries
"""

import pytest
from pytest_bdd import given, scenarios, then, when

scenarios("features/competition_queries.feature")


@pytest.fixture
def ctx():
    return {}


@given("the match data is loaded", target_fixture="match_data")
def match_data_loaded(engine):
    return engine


@when("I request the 2019 Brasileirão standings", target_fixture="standings")
def standings_2019(match_data, ctx):
    ctx["standings"] = match_data.standings(competition="brasileirao", season=2019)
    return ctx["standings"]


@then("the champion should be Flamengo")
def assert_champion(standings):
    assert standings[0]["team"] == "Flamengo"


@then("the champion should have 90 points")
def assert_champion_points(standings):
    assert standings[0]["points"] == 90


@then("there should be 20 teams")
def assert_twenty(standings):
    assert len(standings) == 20


@then("each team should have wins, draws, losses and points")
def assert_team_fields(standings):
    for row in standings:
        for key in ("wins", "draws", "losses", "points"):
            assert key in row


@then("the standings should be sorted by points descending")
def assert_sorted(standings):
    pts = [r["points"] for r in standings]
    assert pts == sorted(pts, reverse=True)
