"""BDD step definitions for competition_queries.feature."""

from __future__ import annotations

from pytest_bdd import parsers, scenarios, then, when

from soccer_mcp import queries as q

scenarios("../features/competition_queries.feature")


@when(parsers.parse('I request the "{competition}" standings for season {season:d}'))
def request_standings(store, context, competition, season):
    context["result"] = q.standings(store, season, competition)


@when("I list the competitions")
def list_comps(store, context):
    result = q.list_competitions(store)
    context["result"] = result
    context["text"] = "; ".join(c["competition"] for c in result["competitions"])


@when("I request the dataset summary")
def dataset_summary(store, context):
    context["result"] = q.dataset_summary(store)


@then(parsers.parse('the leader should be "{team}" with {points:d} points'))
def leader_points(context, team, points):
    top = context["result"]["standings"][0]
    assert top["team"] == team
    assert top["points"] == points


@then("the leader should be marked as champion")
def leader_champion(context):
    assert context["result"]["standings"][0].get("champion") is True


@then(parsers.parse("the table should cover {teams:d} teams and {matches:d} matches"))
def table_coverage(context, teams, matches):
    assert context["result"]["teams"] == teams
    assert context["result"]["matches"] == matches


@then(parsers.parse("exactly {count:d} teams should be marked as relegated"))
def relegated_count(context, count):
    relegated = [r for r in context["result"]["standings"] if r.get("relegated")]
    assert len(relegated) == count


@then(parsers.parse('"{team}" should be relegated'))
def team_relegated(context, team):
    row = [r for r in context["result"]["standings"] if r["team"] == team]
    assert row and row[0].get("relegated") is True


@then("every team's points should equal 3 x wins + draws")
def points_rule(context):
    for row in context["result"]["standings"]:
        assert row["points"] == 3 * row["wins"] + row["draws"]


@then(parsers.parse('the list should include "{text}"'))
def list_includes(context, text):
    assert text in context["text"]


@then(parsers.parse("all {count:d} CSV files should be reported"))
def all_files_reported(context, count):
    assert len(context["result"]["sources"]) == count


@then(parsers.parse("the unified match count should exceed {count:d}"))
def unified_exceeds(context, count):
    assert context["result"]["unified_matches"] > count


@then(parsers.parse("the player count should be {count:d}"))
def player_count(context, count):
    assert context["result"]["players"] == count
