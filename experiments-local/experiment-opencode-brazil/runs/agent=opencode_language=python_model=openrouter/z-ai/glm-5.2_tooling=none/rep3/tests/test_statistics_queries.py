"""BDD step definitions for Statistical Analysis feature.

Context block
-------------
Implements Given/When/Then steps for ``statistics_queries.feature``.
"""
from __future__ import annotations

from pytest_bdd import scenarios, given, when, then, parsers

scenarios("features/statistics_queries.feature")


@given("the match data is loaded", target_fixture="stat_ctx")
def stat_data_loaded(loader):
    assert not loader.matches.empty
    return {"loader": loader, "result": None}


@when(parsers.parse('I request average goals for competition "{competition}"'),
      target_fixture="stat_ctx")
def avg_goals(stat_ctx, queries, competition):
    stat_ctx["result"] = queries["average_goals"](
        stat_ctx["loader"], competition=competition
    )
    return stat_ctx


@when(parsers.parse("I request the top {n:d} biggest wins"),
      target_fixture="stat_ctx")
def biggest(stat_ctx, queries, n):
    stat_ctx["result"] = queries["biggest_wins"](
        stat_ctx["loader"], limit=n
    )
    return stat_ctx


@when(parsers.parse('I request the top {n:d} biggest wins in "{competition}"'),
      target_fixture="stat_ctx")
def biggest_comp(stat_ctx, queries, n, competition):
    stat_ctx["result"] = queries["biggest_wins"](
        stat_ctx["loader"], competition=competition, limit=n
    )
    return stat_ctx


@then("I should receive an average goals value greater than zero")
def avg_gt_zero(stat_ctx):
    assert stat_ctx["result"]["average_goals"] > 0


@then("the home win rate should be between 0 and 100")
def home_win_rate_range(stat_ctx):
    wr = stat_ctx["result"]["home_win_rate"]
    assert 0 <= wr <= 100


@then("I should receive at most 5 results")
def at_most_five(stat_ctx):
    assert len(stat_ctx["result"]) <= 5


@then("each result should have a winner, loser, score, and margin")
def biggest_fields(stat_ctx):
    for r in stat_ctx["result"]:
        for key in ("winner", "loser", "score", "margin"):
            assert key in r


@then("the margins should be sorted in descending order")
def margins_sorted(stat_ctx):
    margins = [r["margin"] for r in stat_ctx["result"]]
    assert margins == sorted(margins, reverse=True)
