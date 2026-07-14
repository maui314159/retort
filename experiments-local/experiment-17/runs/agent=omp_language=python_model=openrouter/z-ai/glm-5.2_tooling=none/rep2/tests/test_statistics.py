"""BDD step definitions for statistical-analysis scenarios."""

from __future__ import annotations

from pytest_bdd import scenarios, when, then, parsers

from brazilian_soccer import queries as Q
from brazilian_soccer.queries import DERBIES

scenarios("features/statistics.feature")


@when(parsers.parse('I request average goals for "{competition}" in season {season:d}'))
def avg_goals(data, ctx, competition, season):
    ctx["stats"] = Q.average_goals(data, competition=competition, season=season)


@when(parsers.parse("I request the {n:d} biggest wins"))
def biggest_wins(data, ctx, n):
    ctx["wins"] = Q.biggest_wins(data, limit=n)


@when(parsers.parse('I request the best home record in "{competition}" for season {season:d}'))
def best_home(data, ctx, competition, season):
    ctx["best"] = Q.best_record(data, venue="home", competition=competition,
                                season=season, limit=5)


@when(parsers.parse("I request derbies for season {season:d}"))
def derbies(data, ctx, season):
    ctx["derbies"] = Q.derby_matches(data, season=season)


@then(parsers.parse("the average goals should be between {lo:d} and {hi:d}"))
def assert_avg_range(ctx, lo, hi):
    assert lo <= ctx["stats"]["avg_goals"] <= hi, ctx["stats"]


@then("the win rates should sum to 1")
def assert_rates_sum(ctx):
    s = ctx["stats"]
    total = s["home_win_rate"] + s["away_win_rate"] + s["draw_rate"]
    assert abs(total - 1.0) < 1e-6, total


@then(parsers.parse("I should receive at most {n:d} results"))
def assert_at_most(ctx, n):
    assert len(ctx["wins"]) <= n


@then("the results should be sorted by margin descending")
def assert_margin_sorted(ctx):
    margins = [w["margin"] for w in ctx["wins"]]
    assert margins == sorted(margins, reverse=True), margins


@then(parsers.parse("every margin should be at least {n:d}"))
def assert_margin_min(ctx, n):
    for w in ctx["wins"]:
        assert w["margin"] >= n, w


@then("I should receive a ranked list")
def assert_ranked(ctx):
    assert len(ctx["best"]) > 0


@then("the win rates should be descending")
def assert_rates_desc(ctx):
    rates = [r["win_rate"] for r in ctx["best"]]
    assert rates == sorted(rates, reverse=True), rates


@then("every derby match should have a derby label")
def assert_derby_label(ctx):
    for m in ctx["derbies"]:
        assert m.get("derby"), m


@then("each derby should be between a known rival pair")
def assert_known_pair(data, ctx):
    pairs = {frozenset((a, b)) for a, b, _ in DERBIES}
    for m in ctx["derbies"]:
        ha = data.resolve_team(m["home"])
        aw = data.resolve_team(m["away"])
        assert frozenset((ha, aw)) in pairs, (m["home"], m["away"])
