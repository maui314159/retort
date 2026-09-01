"""BDD steps for team_queries.feature."""

from __future__ import annotations

from pytest_bdd import parsers, scenarios, then, when

import brazilian_soccer.analysis as an

scenarios("features/team_queries.feature")


@when(
    parsers.parse(
        'I request statistics for "{team}" in season "{season}" in competition "{competition}"'
    )
)
def stats_season_competition(dataset, ctx, team, season, competition):
    ctx["stats"] = an.team_stats(dataset, team, season=int(season), competition=competition)


@when(parsers.parse('I request statistics for "{team}" in season "{season}"'))
def stats_season(dataset, ctx, team, season):
    ctx["stats"] = an.team_stats(dataset, team, season=int(season))


@when(parsers.parse('I compare "{team_a}" and "{team_b}" head-to-head'))
def compare_h2h(dataset, ctx, team_a, team_b):
    ctx["h2h"] = an.head_to_head(dataset, team_a, team_b, limit=500)


@when(parsers.parse('I request the profile for "{team}"'))
def profile(dataset, ctx, team):
    ctx["profile"] = an.team_profile(dataset, team)


@when(parsers.parse('I request statistics for "{team}" in season "2023"'))
def stats_variant(dataset, ctx, team):
    ctx["stats"] = an.team_stats(dataset, team, season=2023)


@when("I compute the 2023 Brasileirão standings")
def standings_2023(dataset, ctx):
    ctx["standings"], _notes = an.standings(dataset, "Brasileirão", 2023)


@then("I should receive wins, losses, draws, and goals")
def received_stats(ctx):
    s = ctx["stats"]
    for rec in (s.overall, s.home, s.away):
        assert rec.matches > 0
        assert rec.wins + rec.draws + rec.losses == rec.matches
        assert rec.goals_for >= 0 and rec.goals_against >= 0


@then("the home record should cover 19 matches")
def home_19(ctx):
    assert ctx["stats"].home.matches == 19


@then("the overall record should cover more matches than the Brasileirão alone")
def overall_more(ctx):
    s = ctx["stats"]
    assert s.overall.matches > 38


@then("the wins, draws and losses should add up to the number of matches")
def h2h_sums(ctx):
    h = ctx["h2h"]
    assert h.wins_a + h.wins_b + h.draws == h.total


@then("the head-to-head should include at least 40 matches")
def h2h_40(ctx):
    assert ctx["h2h"].total >= 40


@then(parsers.parse('the profile should list competitions including "{competition}"'))
def profile_has_competition(ctx, competition):
    names = [e.competition for e in ctx["profile"].entries]
    assert any(competition in n for n in names)


@then("the profile should show matches across more than one competition")
def profile_multi(ctx):
    assert len(ctx["profile"].entries) > 1


@then(parsers.parse('the statistics should be for "{team}"'))
def stats_display(ctx, team):
    assert ctx["stats"].team.display == team


@then("the top-scoring team should have scored at least 60 goals")
def top_scorer_60(ctx):
    rows = ctx["standings"].rows
    top = max(rows, key=lambda r: r.goals_for)
    ctx["top_scorer"] = top
    assert top.goals_for >= 60


@then("no team should have scored more goals than the top-scoring team")
def top_scorer_max(ctx):
    top = ctx["top_scorer"]
    assert all(top.goals_for >= r.goals_for for r in ctx["standings"].rows)
