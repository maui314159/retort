"""BDD steps for competition_queries.feature."""

from __future__ import annotations

from pytest_bdd import parsers, scenarios, then, when

import brazilian_soccer.analysis as an

scenarios("features/competition_queries.feature")


@when(parsers.parse('I ask for the champion of "{competition}" in season "{season}"'))
def ask_champion(dataset, ctx, competition, season):
    ctx["champion"] = an.champion(dataset, competition, int(season))


@when(parsers.parse('I request the standings of "{competition}" for season "{season}"'))
def request_standings(dataset, ctx, competition, season):
    try:
        ctx["standings"], ctx["notes"] = an.standings(dataset, competition, int(season))
        ctx["error"] = None
    except an.AnalysisError as exc:
        ctx["standings"] = None
        ctx["error"] = str(exc)


@when(parsers.parse('I list the finals of the "{competition}"'))
def list_finals(dataset, ctx, competition):
    ctx["finals"] = an.competition_finals(dataset, competition)


@when(parsers.parse('I request the competitions of team "{team}"'))
def team_comps(dataset, ctx, team):
    ctx["profile"] = an.team_competitions(dataset, team)


@when("I list all competitions")
def list_all_comps(dataset, ctx):
    ctx["competitions"] = an.list_competitions(dataset)


@then(parsers.parse('the champion should be "{team}"'))
def champion_is(ctx, team):
    assert ctx["champion"]["champion"] == team


@then(parsers.parse("the champion should have {points:d} points"))
def champion_points(ctx, points):
    assert ctx["champion"]["champion_key"]
    assert str(points) in ctx["champion"]["record"], ctx["champion"]["record"]


@then("the table should have 20 teams")
def twenty_teams(ctx):
    assert len(ctx["standings"].rows) == 20


@then("every team should play 38 matches")
def all_38(ctx):
    assert all(row.played == 38 for row in ctx["standings"].rows)


@then(parsers.parse('the leader should be "{team}"'))
def leader_is(ctx, team):
    assert ctx["standings"].champion.team == team


@then(parsers.parse('the relegated teams should include "{team_a}" and "{team_b}"'))
def relegated_includes(ctx, team_a, team_b):
    relegated = [r.team for r in ctx["standings"].relegated]
    assert team_a in relegated
    assert team_b in relegated


@then("at least 6 finals should be listed")
def six_finals(ctx):
    assert len(ctx["finals"]) >= 6


@then(parsers.parse('the 2019 Libertadores champion should be "{team}"'))
def lib_2019(ctx, team):
    final_2019 = next(f for f in ctx["finals"] if f.season == 2019)
    assert final_2019.winner_display == team


@then("the answer should note that the final was level on aggregate")
def pens_note(ctx):
    assert ctx["champion"]["notes"]
    assert "penalties" in ctx["champion"]["notes"][0]


@then("the request should explain that cups have no standings")
def cup_no_standings(ctx):
    assert ctx["error"] is not None
    assert "standings" in ctx["error"].lower()


@then(
    parsers.parse(
        'the answer should include "Brasileirão", "Copa do Brasil" and "Libertadores"'
    )
)
def palmeiras_comps(ctx):
    names = [e.competition for e in ctx["profile"].entries]
    assert any("Brasileirão Serie A" == n for n in names)
    assert any("Copa do Brasil" == n for n in names)
    assert any("Copa Libertadores" == n for n in names)


@then("all five competitions should be listed")
def five_comps(ctx):
    assert len(ctx["competitions"]) == 5


@then("each competition should list its season coverage")
def comp_seasons(ctx):
    for c in ctx["competitions"]:
        assert c.seasons
        assert c.match_count > 0
        assert c.team_count > 0
