"""Step definitions for match_queries.feature."""

from __future__ import annotations

from datetime import date

from pytest_bdd import parsers, scenarios, then, when

import query_engine as qe

scenarios("features/match_queries.feature")


@when(parsers.parse('I search for matches between "{team1}" and "{team2}"'))
def search_between(store, context, team1, team2):
    context["result"] = qe.find_matches(team=team1, opponent=team2,
                                        limit=50, store=store)


@when(parsers.parse('I search for matches of "{team}" in season {season:d}'))
def search_team_season(store, context, team, season):
    context["result"] = qe.find_matches(team=team, season=season, limit=100,
                                        store=store)


@when(parsers.parse('I search for matches of "{team}" in competition "{comp}"'))
def search_team_competition(store, context, team, comp):
    context["result"] = qe.find_matches(team=team, competition=comp,
                                        limit=100, store=store)


@when(parsers.parse(
    'I search for matches of "{team}" between "{date_from}" and "{date_to}"'))
def search_team_dates(store, context, team, date_from, date_to):
    context["result"] = qe.find_matches(team=team, date_from=date_from,
                                        date_to=date_to, limit=100,
                                        store=store)


@when(parsers.parse('I compare "{team1}" and "{team2}" head-to-head'))
def compare_h2h(store, context, team1, team2):
    context["result"] = qe.head_to_head(team1, team2, limit=100, store=store)


@when(parsers.parse(
    'I search for matches of "{team}" in competition "{comp}" and season '
    '{season:d}'))
def search_team_comp_season(store, context, team, comp, season):
    result = qe.find_matches(team=team, competition=comp, season=season,
                             limit=100, store=store)
    context.setdefault("results", []).append(result)
    context["result"] = result


@when(parsers.parse('I search for matches in competition "{comp}" at stage '
                    '"{stage}"'))
def search_by_stage(store, context, comp, stage):
    context["result"] = qe.find_matches(competition=comp, stage=stage,
                                        limit=100, store=store)


@then("I should receive a list of matches")
def check_list(context):
    assert context["result"]["total"] > 0
    assert len(context["result"]["matches"]) > 0


@then("each match should have date, scores, and competition")
def check_fields(context):
    for match in context["result"]["matches"]:
        assert match["date"] is not None
        assert match["home_goals"] is not None
        assert match["away_goals"] is not None
        assert match["competition"]


@then(parsers.parse('every match should involve both "{team1}" and "{team2}"'))
def check_both_teams(context, team1, team2):
    for match in context["result"]["matches"]:
        pair = {match["home_team"], match["away_team"]}
        assert pair == {team1, team2}


@then(parsers.parse("I should receive at least {minimum:d} matches"))
def check_minimum(context, minimum):
    assert context["result"]["total"] >= minimum


@then(parsers.parse('every match should involve "{team}"'))
def check_involves(context, team):
    for match in context["result"]["matches"]:
        assert team in (match["home_team"], match["away_team"])


@then(parsers.parse(
    'every returned match should be from competition "{competition}"'))
def check_competition(context, competition):
    assert context["result"]["total"] > 0
    for match in context["result"]["matches"]:
        assert match["competition"] == competition


@then(parsers.parse(
    'every returned match date should be within "{date_from}" and "{date_to}"'))
def check_dates(context, date_from, date_to):
    start = date.fromisoformat(date_from)
    end = date.fromisoformat(date_to)
    assert context["result"]["total"] > 0
    for match in context["result"]["matches"]:
        day = date.fromisoformat(match["date"])
        assert start <= day <= end


@then("the summary should contain wins for both teams and draws")
def check_summary_keys(context):
    summary = context["result"]["summary"]
    team1 = context["result"]["team1"]
    team2 = context["result"]["team2"]
    assert f"{team1}_wins" in summary
    assert f"{team2}_wins" in summary
    assert "draws" in summary


@then("the summary counts should add up to the total number of matches")
def check_summary_total(context):
    result = context["result"]
    total = sum(result["summary"].values())
    assert total == result["total_matches"]
    assert len(result["matches"]) == result["total_matches"]


@then("I should receive an empty list of matches")
def check_empty(context):
    assert context["result"]["total"] == 0
    assert context["result"]["matches"] == []


@then("both searches should return the same number of matches")
def check_same_count(context):
    results = context["results"]
    assert len(results) == 2
    assert results[0]["total"] == results[1]["total"]
    assert results[0]["total"] == 38


@then(parsers.parse('every returned match should be at stage "{stage}"'))
def check_stage(context, stage):
    for match in context["result"]["matches"]:
        assert match["stage"] == stage
