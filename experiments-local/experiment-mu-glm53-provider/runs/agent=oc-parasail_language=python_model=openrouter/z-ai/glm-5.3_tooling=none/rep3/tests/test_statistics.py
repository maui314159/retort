"""BDD steps for statistics.feature."""

from __future__ import annotations

from pytest_bdd import parsers, scenarios, then, when

import brazilian_soccer.analysis as an

scenarios("features/statistics.feature")


@when(parsers.parse('I request competition statistics for "{competition}"'))
def comp_stats(dataset, ctx, competition):
    ctx["stats"] = an.competition_stats(dataset, competition=competition)


@when("I request competition statistics for all competitions")
def all_stats(dataset, ctx):
    ctx["stats"] = an.competition_stats(dataset)


@when(parsers.parse('I request competition statistics for "{competition}" season "{season}"'))
def comp_stats_season(dataset, ctx, competition, season):
    ctx["stats"] = an.competition_stats(dataset, competition=competition, season=int(season))


@when("I request the biggest wins")
def biggest(dataset, ctx):
    ctx["wins"] = an.biggest_wins(dataset, limit=10)


@when(parsers.parse('I request the best away records for "{competition}" season "{season}"'))
def best_away(dataset, ctx, competition, season):
    ctx["best_away"] = an.best_records(
        dataset, venue="away", competition=competition, season=int(season), min_matches=5
    )


@when(parsers.parse('I compare seasons {a:d} and {b:d} of the "{competition}"'))
def compare(dataset, ctx, a, b, competition):
    ctx["comparison"] = an.compare_seasons(dataset, a, b, competition=competition)


@when(parsers.parse('I request the derbies of season "{season}"'))
def season_derbies(dataset, ctx, season):
    ctx["derbies"] = an.derbies(dataset, season=int(season))


@then(parsers.parse("the average goals per match should be between {low:d} and {high:d}"))
def avg_goals_between(ctx, low, high):
    assert low <= ctx["stats"]["avg_goals"] <= high, ctx["stats"]["avg_goals"]


@then("the home win rate should be higher than the away win rate")
def home_gt_away(ctx):
    assert ctx["stats"]["home_win_pct"] > ctx["stats"]["away_win_pct"]


@then(parsers.parse("the biggest margin should be at least {margin:d} goals"))
def margin_at_least(ctx, margin):
    assert ctx["wins"][0].margin >= margin


@then("the results should be sorted by margin descending")
def sorted_margins(ctx):
    margins = [m.margin for m in ctx["wins"]]
    assert margins == sorted(margins, reverse=True)


@then(parsers.parse('the best away team should be "{team}"'))
def best_away_team(ctx, team):
    assert ctx["best_away"][0][0].display == team


@then("the home win rate should be above 40 percent")
def home_above_40(ctx):
    assert ctx["stats"]["home_win_pct"] > 40


@then("the away win rate should be below 30 percent")
def away_below_30(ctx):
    assert ctx["stats"]["away_win_pct"] < 30


@then(parsers.parse('the {season:d} champion should be "{team}"'))
def season_champion(ctx, season, team):
    key = "champion_a" if season == ctx["comparison"]["season_a"] else "champion_b"
    assert ctx["comparison"][key]["champion"] == team


@then("both seasons should average at least 2 goals per match")
def both_avg_2(ctx):
    assert ctx["comparison"]["stats_a"]["avg_goals"] >= 2
    assert ctx["comparison"]["stats_b"]["avg_goals"] >= 2


@then("at least 10 named derbies should have matches")
def ten_derbies(ctx):
    assert len(ctx["derbies"]) >= 10


@then("the Fla-Flu derby should appear")
def fla_flu(ctx):
    labels = [d.label for d in ctx["derbies"]]
    assert "Fla-Flu" in labels
