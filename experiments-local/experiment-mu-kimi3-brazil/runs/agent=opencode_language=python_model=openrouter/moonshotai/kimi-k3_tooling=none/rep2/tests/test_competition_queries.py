"""Step definitions for competition_queries.feature."""

from __future__ import annotations

from pytest_bdd import parsers, then, when, scenarios

scenarios("features/competition_queries.feature")


# ---------------------------------------------------------------------------
# When
# ---------------------------------------------------------------------------

@when(parsers.parse("I request the standings for season {season:d}"))
def request_standings(engine, context, season):
    context["result"] = engine.standings(season)


@when(parsers.parse('I ask which competitions "{team}" has played in'))
def request_team_competitions(engine, context, team):
    context["result"] = engine.team_competitions(team)


# ---------------------------------------------------------------------------
# Then
# ---------------------------------------------------------------------------

@then(parsers.parse('the champion should be "{team}"'))
def check_champion(context, team):
    assert context["result"]["champion"] == team
    assert context["result"]["standings"][0]["tag"] == "Champion"


@then(parsers.parse("the standings should have {count:d} teams"))
def check_team_count(context, count):
    assert len(context["result"]["standings"]) == count


@then("every team should have points equal to 3 per win plus 1 per draw")
def check_points(context):
    for row in context["result"]["standings"]:
        assert row["points"] == 3 * row["wins"] + row["draws"]


@then(parsers.parse("every team should have played {count:d} matches"))
def check_played(context, count):
    for row in context["result"]["standings"]:
        assert row["played"] == count
        assert row["played"] == row["wins"] + row["draws"] + row["losses"]


@then(parsers.parse("exactly {count:d} teams should be tagged as relegated"))
def check_relegated(context, count):
    assert len(context["result"]["relegated"]) == count


@then(parsers.parse('the answer should include "{competition}"'))
def check_competition_included(context, competition):
    assert competition in context["result"]["competitions"]
