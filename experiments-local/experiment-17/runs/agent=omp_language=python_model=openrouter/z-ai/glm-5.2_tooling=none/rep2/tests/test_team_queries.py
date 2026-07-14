"""BDD step definitions for team-query scenarios."""

from __future__ import annotations

from pytest_bdd import scenarios, when, then, parsers

from brazilian_soccer import queries as Q

scenarios("features/team_queries.feature")


@when(parsers.parse('I request statistics for "{team}" in season {season:d}'))
def request_stats(data, ctx, team, season):
    ctx["stats"] = Q.team_stats(data, team, season=season)


@when(parsers.parse('I request home statistics for "{team}" in season {season:d} and competition "{competition}"'))
def request_home_stats(data, ctx, team, season, competition):
    ctx["stats"] = Q.team_stats(data, team, season=season, venue="home",
                                competition=competition)
@when(parsers.parse('I compare "{a}" and "{b}" head-to-head'))
def compare_h2h(data, ctx, a, b):
    ctx["h2h"] = Q.head_to_head(data, a, b)


@when(parsers.parse('I request the competitions of "{team}"'))
def request_comps(data, ctx, team):
    ctx["comps"] = Q.team_competitions(data, team)


@then("I should receive wins, losses, draws, and goals")
def assert_stats_fields(ctx):
    s = ctx["stats"]
    for k in ("wins", "losses", "draws", "goals_for", "goals_against",
              "matches", "win_rate"):
        assert k in s, k


@then("the matches count should be positive")
def assert_matches_positive(ctx):
    assert ctx["stats"]["matches"] > 0


@then("the home record should be present")
def assert_home_present(ctx):
    s = ctx["stats"]
    # venue='home' still returns the flat stats; matches>0 confirms data.
    assert s["matches"] > 0


@then("home matches should be at most 19")
def assert_home_at_most_19(ctx):
    # A Brasileirão season has at most 19 home matches per team.
    assert ctx["stats"]["matches"] <= 19, ctx["stats"]


@then("I should receive a head-to-head record")
def assert_h2h(ctx):
    h = ctx["h2h"]
    for k in ("matches", "team_a_wins", "team_b_wins", "draws",
              "team_a_goals", "team_b_goals"):
        assert k in h, k


@then("the wins plus draws plus losses should equal the match count")
def assert_h2h_totals(ctx):
    h = ctx["h2h"]
    total = h["team_a_wins"] + h["team_b_wins"] + h["draws"]
    assert total == h["matches"], (total, h["matches"])


@then("I should receive a non-empty competition map")
def assert_comps_nonempty(ctx):
    assert ctx["comps"], ctx["comps"]


@then(parsers.parse('the map should include "{comp}"'))
def assert_comps_includes(ctx, comp):
    assert comp in ctx["comps"], (comp, ctx["comps"])
