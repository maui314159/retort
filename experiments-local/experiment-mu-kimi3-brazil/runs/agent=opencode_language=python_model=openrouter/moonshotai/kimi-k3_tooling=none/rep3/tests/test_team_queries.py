"""Step definitions for team_queries.feature."""

from __future__ import annotations

from pytest_bdd import parsers, scenarios, then, when

import query_engine as qe

scenarios("features/team_queries.feature")


@when(parsers.parse('I request home statistics for "{team}" in season '
                    '{season:d}'))
def home_stats(store, context, team, season):
    context["result"] = qe.team_statistics(team, season=season, venue="home",
                                           store=store)


@when(parsers.parse('I request statistics for "{team}" in season {season:d}'))
def season_stats(store, context, team, season):
    context["result"] = qe.team_statistics(team, season=season, store=store)


@when(parsers.parse('I list the teams of competition "{comp}" in season '
                    '{season:d}'))
def list_teams_step(store, context, comp, season):
    context["result"] = qe.list_teams(competition=comp, season=season,
                                      store=store)


@then("I should receive wins, losses, draws, and goals")
def check_record_fields(context):
    result = context["result"]
    for field in ("wins", "losses", "draws", "goals_for", "goals_against"):
        assert field in result
        assert isinstance(result[field], int)


@then("the record should contain more than 0 matches")
def check_matches_positive(context):
    assert context["result"]["matches"] > 0


@then("wins plus draws plus losses should equal matches played")
def check_record_sum(context):
    result = context["result"]
    total = result["wins"] + result["draws"] + result["losses"]
    assert total == result["matches"]


@then("the win rate should be between 0 and 100")
def check_win_rate(context):
    assert 0.0 <= context["result"]["win_rate_pct"] <= 100.0


@then("the result should include statistics per competition")
def check_breakdown(context):
    assert "by_competition" in context["result"]
    assert len(context["result"]["by_competition"]) > 0


@then(parsers.parse('the breakdown should include "{competition}"'))
def check_breakdown_comp(context, competition):
    assert competition in context["result"]["by_competition"]


@then(parsers.parse("I should receive exactly {count:d} teams"))
def check_team_count(context, count):
    assert context["result"]["total"] == count
    assert len(context["result"]["teams"]) == count


@then(parsers.parse('the list should include "{team1}" and "{team2}"'))
def check_teams_present(context, team1, team2):
    assert team1 in context["result"]["teams"]
    assert team2 in context["result"]["teams"]
