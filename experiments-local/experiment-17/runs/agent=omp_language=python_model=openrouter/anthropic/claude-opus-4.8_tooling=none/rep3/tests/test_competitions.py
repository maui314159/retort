"""
================================================================================
tests.test_competitions
================================================================================
Context:
    BDD step definitions for tests/features/competitions.feature. Validates
    standings computation against known ground truth (2019 Brasileirao:
    Flamengo champion, 90 pts, 38 games), champion lookup, aggregate-statistics
    plausibility and biggest-wins ordering.
================================================================================
"""

from pytest_bdd import parsers, scenarios, then, when

scenarios("features/competitions.feature")


@when(parsers.parse('I compute the {season:d} "{comp}" standings'))
def _standings(graph, context, season, comp):
    context["rows"] = graph.standings(comp, season)
    context["graph"] = graph


@when(parsers.parse('I ask who won the {season:d} "{comp}"'))
def _champion(graph, context, season, comp):
    context["champ"] = graph.champion(comp, season)
    context["graph"] = graph


@when(parsers.parse('I compute aggregate statistics for "{comp}"'))
def _agg(graph, context, comp):
    context["stats"] = graph.aggregate_stats(competition=comp)


@when(parsers.parse('I list the biggest wins in "{comp}"'))
def _biggest(graph, context, comp):
    context["wins"] = graph.biggest_wins(competition=comp, limit=10)


@then(parsers.parse('the champion should be "{name}"'))
def _champ_is(context, name):
    key = context["rows"][0][0]
    assert context["graph"].resolve_team(name) == key


@then(parsers.parse("the champion should have {pts:d} points"))
def _champ_points(context, pts):
    assert context["rows"][0][1].points == pts


@then(parsers.parse("the top team should have played {games:d} matches"))
def _champ_games(context, games):
    assert context["rows"][0][1].matches == games


@then(parsers.parse('the answer should name "{name}"'))
def _answer_names(context, name):
    key = context["champ"][0]
    assert context["graph"].resolve_team(name) == key


@then(parsers.parse("the average goals per match should be between {lo:d} and {hi:d}"))
def _avg_goals(context, lo, hi):
    assert lo <= context["stats"]["avg_goals_per_match"] <= hi


@then("the home win rate should be greater than the away win rate")
def _home_gt_away(context):
    assert context["stats"]["home_win_rate"] > context["stats"]["away_win_rate"]


@then("each win should have a margin not greater than the previous one")
def _margins_desc(context):
    margins = [abs(m.home_goal - m.away_goal) for m in context["wins"]]
    assert margins == sorted(margins, reverse=True)
    assert margins and margins[0] >= 5
