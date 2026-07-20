"""Step definitions for competition_queries.feature."""

from __future__ import annotations

from pytest_bdd import parsers, scenarios, then, when

import query_engine as qe

scenarios("features/competition_queries.feature")


@when(parsers.parse('I request the standings of competition "{comp}" for '
                    'season {season:d}'))
def standings(store, context, comp, season):
    context["result"] = qe.competition_standings(season=season,
                                                 competition=comp,
                                                 store=store)


@when(parsers.parse('I request the top scoring teams of competition "{comp}" '
                    'for season {season:d}'))
def top_scoring(store, context, comp, season):
    context["result"] = qe.top_scoring_teams(competition=comp, season=season,
                                             store=store)


@when("I list the competitions")
def list_competitions(store, context):
    context["result"] = qe.list_competitions(store=store)


@then(parsers.parse("the standings should contain {count:d} teams"))
def check_standings_size(context, count):
    assert context["result"]["total_teams"] == count
    assert len(context["result"]["standings"]) == count


@then(parsers.parse('the champion should be "{team}" with {points:d} points'))
def check_champion(context, team, points):
    leader = context["result"]["standings"][0]
    assert leader["position"] == 1
    assert leader["team"] == team
    assert leader["points"] == points
    assert leader.get("champion") is True


@then(parsers.parse("every team should have played {matches:d} matches"))
def check_played(context, matches):
    for row in context["result"]["standings"]:
        assert row["played"] == matches


@then("points should equal 3 per win plus 1 per draw for every team")
def check_points(context):
    for row in context["result"]["standings"]:
        assert row["points"] == row["wins"] * 3 + row["draws"]


@then("the bottom 4 teams should occupy positions 17 to 20")
def check_relegation_zone(context):
    bottom = context["result"]["standings"][-4:]
    assert [row["position"] for row in bottom] == [17, 18, 19, 20]


@then(parsers.parse('the first team should be "{team}" with {goals:d} goals'))
def check_top_scorer(context, team, goals):
    first = context["result"]["teams"][0]
    assert first["team"] == team
    assert first["goals"] == goals


@then(parsers.parse('the list should include "{comp1}", "{comp2}" and '
                    '"{comp3}"'))
def check_competitions(context, comp1, comp2, comp3):
    names = {c["competition"] for c in context["result"]["competitions"]}
    assert {comp1, comp2, comp3} <= names


@then(parsers.parse('"{comp}" should cover seasons {first:d} to {last:d}'))
def check_season_range(context, comp, first, last):
    entry = next(c for c in context["result"]["competitions"]
                 if c["competition"] == comp)
    assert min(entry["seasons"]) == first
    assert max(entry["seasons"]) == last
