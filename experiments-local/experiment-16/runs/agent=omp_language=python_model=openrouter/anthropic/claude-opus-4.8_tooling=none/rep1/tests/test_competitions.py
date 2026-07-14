"""
================================================================================
Context
--------------------------------------------------------------------------------
Module  : tests.test_competitions
Purpose : BDD steps for features/competitions.feature - standings, average
          goals, biggest wins and best venue records computed from results.
================================================================================
"""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/competitions.feature")


@given("the soccer knowledge graph is loaded", target_fixture="graph")
def _loaded(sample_graph):
    return sample_graph


@when(parsers.parse('I request the "{comp}" standings for season {season:d}'))
def _standings(graph, ctx, comp, season):
    ctx["table"] = graph.standings(comp, season)


@when(parsers.parse('I request the average goals for the "{comp}"'))
def _avg(graph, ctx, comp):
    ctx["avg"] = graph.average_goals(comp)


@when("I request the biggest wins overall")
def _big(graph, ctx):
    ctx["big"] = graph.biggest_wins(limit=5)


@when(parsers.parse("I request the best home records with at least {n:d} match"))
def _best(graph, ctx, n):
    ctx["best"] = graph.best_records(venue="home", min_matches=n)


@then("the table should be ordered by points descending")
def _ordered(ctx):
    pts = [r.points for r in ctx["table"]]
    assert pts == sorted(pts, reverse=True)


@then("points should equal wins times three plus draws")
def _points(ctx):
    assert all(r.points == r.wins * 3 + r.draws for r in ctx["table"])


@then("the average goals per match should be greater than 0")
def _avg_pos(ctx):
    assert ctx["avg"]["avg_goals_per_match"] > 0


@then("the home win rate should be between 0 and 1")
def _wr(ctx):
    assert 0.0 <= ctx["avg"]["home_win_rate"] <= 1.0


@then("the first match should have the largest goal margin")
def _margin(ctx):
    margins = [abs(m.home_goal - m.away_goal) for m in ctx["big"]]
    assert margins[0] == max(margins)


@then("the teams should be ordered by win rate descending")
def _best_ordered(ctx):
    rates = [r.win_rate for r in ctx["best"]]
    assert rates == sorted(rates, reverse=True)
