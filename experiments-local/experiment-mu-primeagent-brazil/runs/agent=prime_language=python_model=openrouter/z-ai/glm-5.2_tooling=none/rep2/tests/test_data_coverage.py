"""
Context block
=============
Brazilian Soccer MCP Server - BDD Step Definitions: Data Coverage
"""

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/data_coverage.feature")


@pytest.fixture
def ctx():
    return {}


@given("the data is loaded", target_fixture="data")
def data_loaded(engine):
    return engine


@then("the matches dataframe should contain rows from every match dataset")
def assert_match_datasets(data):
    comps = set(data.data.matches["competition"].dropna().unique())
    expected = {"Brasileirão Serie A", "Copa do Brasil", "Copa Libertadores",
                "Serie A", "Serie B", "Serie C", "Brasileirão (2003-2019)"}
    assert expected <= comps, comps


@then("the players dataframe should contain FIFA players")
def assert_players(data):
    assert len(data.data.players) > 1000


@then(parsers.parse('"{a}" and "{b}" should map to the same team'))
def assert_same_team(data, a, b):
    from brazilian_soccer_mcp.normalizer import canonical_key
    assert canonical_key(a) == canonical_key(b), (a, b)


@when(parsers.parse('I request players at "{club}" and the head to head of "{a}" against "{b}"'),
      target_fixture="crossfile")
def crossfile(data, ctx, club, a, b):
    ctx["players"] = data.players_at_club(club)
    ctx["h2h"] = data.head_to_head(a, b)
    return ctx


@then("both queries should return results")
def assert_crossfile(crossfile):
    assert len(crossfile["players"]) > 0
    assert crossfile["h2h"]["matches"] > 0
