"""BDD step definitions for Team Queries feature.

Context block
-------------
Implements Given/When/Then steps for ``team_queries.feature``.
"""
from __future__ import annotations

from pytest_bdd import scenarios, given, when, then, parsers

scenarios("features/team_queries.feature")


@given("the match data is loaded", target_fixture="team_ctx")
def team_data_loaded(loader):
    assert not loader.matches.empty
    return {"loader": loader, "result": None}


@when(parsers.parse('I request statistics for "{team}" in season {season:d}'),
      target_fixture="team_ctx")
def stats_for_team(team_ctx, queries, team, season):
    team_ctx["result"] = queries["team_statistics"](
        team_ctx["loader"], team, season=season
    )
    return team_ctx


@when(parsers.parse('I request home statistics for "{team}" in season {season:d}'),
      target_fixture="team_ctx")
def home_stats(team_ctx, queries, team, season):
    team_ctx["result"] = queries["team_statistics"](
        team_ctx["loader"], team, season=season, venue="home"
    )
    return team_ctx


@when(parsers.parse('I compare "{team_a}" and "{team_b}"'),
      target_fixture="team_ctx")
def compare(team_ctx, queries, team_a, team_b):
    team_ctx["result"] = queries["compare_teams"](
        team_ctx["loader"], team_a, team_b
    )
    return team_ctx


@when(parsers.parse('I request the home vs away record for "{team}" in season {season:d}'),
      target_fixture="team_ctx")
def home_away(team_ctx, queries, team, season):
    team_ctx["result"] = queries["home_vs_away_record"](
        team_ctx["loader"], team, season=season
    )
    return team_ctx


@then("I should receive wins, losses, draws, and goals")
def team_stats_fields(team_ctx):
    r = team_ctx["result"]
    for key in ("wins", "losses", "draws", "goals_for", "goals_against"):
        assert key in r


@then("the matches count should equal wins plus draws plus losses")
def team_stats_total(team_ctx):
    r = team_ctx["result"]
    assert r["matches"] == r["wins"] + r["draws"] + r["losses"]


@then("the venue should be home")
def venue_is_home(team_ctx):
    assert team_ctx["result"]["venue"] == "home"


@then("the win rate should be between 0 and 100")
def win_rate_range(team_ctx):
    wr = team_ctx["result"]["win_rate"]
    assert 0 <= wr <= 100


@then("I should receive statistics for both teams")
def compare_both(team_ctx):
    r = team_ctx["result"]
    assert "team_a_stats" in r
    assert "team_b_stats" in r


@then("I should receive a head-to-head summary")
def compare_h2h(team_ctx):
    assert "head_to_head" in team_ctx["result"]


@then("I should receive separate home and away statistics")
def home_away_split(team_ctx):
    r = team_ctx["result"]
    assert "home" in r and "away" in r
