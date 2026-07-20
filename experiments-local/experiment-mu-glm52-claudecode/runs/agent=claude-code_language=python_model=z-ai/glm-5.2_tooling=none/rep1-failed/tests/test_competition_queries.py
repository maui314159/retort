"""BDD step definitions for the Competition Queries feature."""

from __future__ import annotations

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from brazilian_soccer_mcp import queries

scenarios("features/competition_queries.feature")


@given("the match data is loaded")
def match_data_loaded(kg):
    assert kg is not None and len(kg.dataset.matches) > 0


@when(
    'I request standings for competition "{competition}" in season {season:d}',
    target_fixture="result",
)
def request_standings(kg, context, competition, season):
    res = queries.competition_standings(kg, competition, season=season, top=30)
    context["result"] = res
    return res


@when(
    'I request info for competition "{competition}"',
    target_fixture="result",
)
def request_comp_info(kg, context, competition):
    res = queries.competition_info(kg, competition)
    context["result"] = res
    return res


@then("I should receive a sorted standings table")
def standings_table(context):
    res = context["result"]
    assert "standings" in res
    rows = res["standings"]
    assert rows, "empty standings"
    # Points should be non-increasing.
    points = [r["points"] for r in rows]
    assert points == sorted(points, reverse=True)


@then('Flamengo should be the champion of the 2019 Brasileirão')
def flamengo_2019_champion(context):
    rows = context["result"]["standings"]
    champion = next(r for r in rows if r["team"] == "Flamengo")
    assert champion.get("champion") is True
    assert champion["position"] == 1


@then('Palmeiras should be the champion of the 2018 Brasileirão')
def palmeiras_2018_champion(context):
    rows = context["result"]["standings"]
    champion = next(r for r in rows if r["team"] == "Palmeiras")
    assert champion.get("champion") is True
    assert champion["position"] == 1


@then("each team should have played a positive number of matches")
def standings_played_positive(context):
    for r in context["result"]["standings"]:
        assert r["played"] > 0


@then("I should receive a seasons list and a teams list")
def comp_info_lists(context):
    res = context["result"]
    assert isinstance(res.get("seasons"), list) and res["seasons"]
    assert isinstance(res.get("teams"), list) and res["teams"]


@then("the total matches should be positive")
def comp_info_total_positive(context):
    assert context["result"]["total_matches"] > 0
