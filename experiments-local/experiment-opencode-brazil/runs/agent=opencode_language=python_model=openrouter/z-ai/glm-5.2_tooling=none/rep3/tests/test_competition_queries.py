"""BDD step definitions for Competition Queries feature.

Context block
-------------
Implements Given/When/Then steps for ``competition_queries.feature``.
"""
from __future__ import annotations

from pytest_bdd import scenarios, given, when, then, parsers

scenarios("features/competition_queries.feature")


@given("the match data is loaded", target_fixture="comp_ctx")
def comp_data_loaded(loader):
    assert not loader.matches.empty
    return {"loader": loader, "result": None}


@when(parsers.parse('I request standings for competition "{competition}" in season {season:d}'),
      target_fixture="comp_ctx")
def standings(comp_ctx, queries, competition, season):
    comp_ctx["result"] = queries["competition_standings"](
        comp_ctx["loader"], competition, season
    )
    return comp_ctx


@when("I list all competitions", target_fixture="comp_ctx")
def list_comps(comp_ctx, queries):
    comp_ctx["result"] = queries["list_competitions"](comp_ctx["loader"])
    return comp_ctx


@when(parsers.parse('I request seasons for competition "{competition}"'),
      target_fixture="comp_ctx")
def seasons(comp_ctx, queries, competition):
    comp_ctx["result"] = queries["competition_seasons"](
        comp_ctx["loader"], competition
    )
    return comp_ctx


@then("I should receive a ranked list of teams")
def ranked_list(comp_ctx):
    assert isinstance(comp_ctx["result"], list)
    assert len(comp_ctx["result"]) > 0
    positions = [t["position"] for t in comp_ctx["result"]]
    assert positions == sorted(positions)


@then("the first team should be labeled Champion")
def first_champion(comp_ctx):
    assert comp_ctx["result"][0].get("label") == "Champion"


@then("each team should have points, wins, draws, and losses")
def team_fields(comp_ctx):
    for t in comp_ctx["result"]:
        for key in ("points", "wins", "draws", "losses"):
            assert key in t


@then("the list should include Brasileirao, Copa do Brasil, and Libertadores")
def list_includes(comp_ctx):
    joined = " ".join(comp_ctx["result"]).lower()
    assert "brasileirao" in joined
    assert "copa do brasil" in joined
    assert "libertadores" in joined


@then("I should receive a list of integer years")
def integer_years(comp_ctx):
    assert isinstance(comp_ctx["result"], list)
    assert all(isinstance(y, int) for y in comp_ctx["result"])
