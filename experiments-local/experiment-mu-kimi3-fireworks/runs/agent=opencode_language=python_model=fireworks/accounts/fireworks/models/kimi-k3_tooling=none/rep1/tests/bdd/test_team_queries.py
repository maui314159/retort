"""BDD step definitions for team_queries.feature."""

from __future__ import annotations

from pytest_bdd import parsers, scenarios, then, when

from soccer_mcp import queries as q

scenarios("../features/team_queries.feature")


@when(parsers.parse('I request statistics for "{team}" in season "{season}"'))
def request_stats(store, context, team, season):
    context["result"] = q.team_stats(store, team, season=season)


@when(parsers.parse('I request home statistics for "{team}" in season {season:d} of "{competition}"'))
def request_home_stats(store, context, team, season, competition):
    context["result"] = q.team_stats(store, team, competition=competition,
                                     season=season, venue="home")


@when(parsers.parse('I ask for the top scoring teams of "{competition}" season {season:d}'))
def top_scoring(store, context, competition, season):
    context["result"] = q.top_scoring_teams(store, competition, season, limit=5)


@when(parsers.parse('I ask which competitions "{team}" has played in'))
def team_comps(store, context, team):
    result = q.team_competitions(store, team)
    context["result"] = result
    context["text"] = "; ".join(c["competition"] for c in result["competitions"])


@when(parsers.parse('I compare "{team1}" and "{team2}" head-to-head'))
def compare_h2h(store, context, team1, team2):
    context["result"] = q.head_to_head(store, team1, team2)


@then("I should receive wins, losses, draws, and goals")
def stats_have_fields(context):
    stats = context["result"]
    for field in ("wins", "losses", "draws", "goals_for", "goals_against"):
        assert field in stats, f"missing field {field}"
    assert stats["matches"] > 0


@then(parsers.parse("the record should show {matches:d} matches"))
def record_matches(context, matches):
    assert context["result"]["matches"] == matches


@then(parsers.parse("the wins, draws and losses should add up to {matches:d}"))
def wdl_add_up(context, matches):
    stats = context["result"]
    assert stats["wins"] + stats["draws"] + stats["losses"] == matches


@then(parsers.parse("the top team should have scored more than {goals:d} goals"))
def top_team_goals(context, goals):
    assert context["result"]["teams"][0]["goals"] > goals


@then(parsers.parse('the answer should include "{text}"'))
def answer_includes(context, text):
    assert text in context["text"]


@then("the head-to-head summary should show wins for both teams and draws")
def h2h_summary(context):
    result = context["result"]
    assert result["team1_wins"] > 0
    assert result["team2_wins"] > 0
    assert result["draws"] > 0


@then("the wins and draws should equal the total matches")
def h2h_totals(context):
    result = context["result"]
    total = result["team1_wins"] + result["team2_wins"] + result["draws"]
    assert total == result["total_matches"]
