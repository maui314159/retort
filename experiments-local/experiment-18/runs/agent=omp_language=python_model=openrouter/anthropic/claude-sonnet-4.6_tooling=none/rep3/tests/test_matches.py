"""
================================================================================
tests.test_matches
================================================================================
Context:
    BDD (Given/When/Then) step definitions for tests/features/matches.feature.
    Exercises the match-query surface of the knowledge graph: team-vs-team,
    by-season, by-competition, and last-meeting lookups, including the
    head-to-head invariant (wins + draws account for every decided meeting).
================================================================================
"""

from pytest_bdd import parsers, scenarios, then, when

from brazil_soccer_mcp.normalize import normalize_competition

scenarios("features/matches.feature")


@when(parsers.parse('I search for matches between "{a}" and "{b}"'))
def _between(graph, context, a, b):
    context["matches"] = graph.find_matches(team=a, opponent=b)
    context["h2h"] = graph.head_to_head(a, b)
    context["team_a"], context["team_b"] = a, b


@when(parsers.parse('I search for "{team}" matches in season {season:d}'))
def _team_season(graph, context, team, season):
    context["matches"] = graph.find_matches(team=team, season=season)
    context["team_key"] = graph.resolve_team(team)
    context["season"] = season


@when(parsers.parse('I search for "{team}" matches in competition "{comp}"'))
def _team_comp(graph, context, team, comp):
    context["matches"] = graph.find_matches(team=team, competition=comp)
    context["competition"] = normalize_competition(comp)


@when(parsers.parse('I ask for the last meeting between "{a}" and "{b}"'))
def _last(graph, context, a, b):
    ms = graph.find_matches(team=a, opponent=b)
    context["last"] = ms[-1] if ms else None


@then("I should receive a list of matches")
def _have_matches(context):
    assert context["matches"], "expected at least one match"


@then("each match should have a date, scores, and competition")
def _match_shape(context):
    for m in context["matches"]:
        assert m.competition
        assert m.date is not None
        assert m.home_goal is not None and m.away_goal is not None


@then("the head-to-head summary should account for all decided meetings")
def _h2h_consistent(context):
    h = context["h2h"]
    decided = [m for m in h["meetings"] if m.home_goal is not None]
    assert h["a_wins"] + h["b_wins"] + h["draws"] == len(decided)


@then(parsers.parse('every returned match should involve "{team}"'))
def _involves(graph, context, team):
    key = graph.resolve_team(team)
    assert context["matches"]
    for m in context["matches"]:
        assert key in (m.home_ckey, m.away_ckey)


@then(parsers.parse("every returned match should be in season {season:d}"))
def _in_season(context, season):
    for m in context["matches"]:
        assert m.season == season


@then(parsers.parse('every returned match should be in competition "{comp}"'))
def _in_comp(context, comp):
    expected = normalize_competition(comp)
    assert context["matches"]
    for m in context["matches"]:
        assert m.competition == expected


@then("I should get a single most recent match with a date")
def _single_last(context):
    last = context["last"]
    assert last is not None
    assert last.date is not None
