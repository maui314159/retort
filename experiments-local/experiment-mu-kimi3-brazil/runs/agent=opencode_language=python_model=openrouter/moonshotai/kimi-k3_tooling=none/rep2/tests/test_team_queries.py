"""Step definitions for team_queries.feature."""

from __future__ import annotations

from pytest_bdd import parsers, then, when, scenarios

scenarios("features/team_queries.feature")


# ---------------------------------------------------------------------------
# When
# ---------------------------------------------------------------------------

@when(parsers.parse('I request statistics for "{team}" in season "{season:d}"'))
def stats_team_season(engine, context, team, season):
    context["result"] = engine.team_statistics(team, season=season)


@when(parsers.parse('I request statistics for "{team}" in season "{season:d}" at "{venue}"'))
def stats_team_season_venue(engine, context, team, season, venue):
    context["result"] = engine.team_statistics(team, season=season, venue=venue)


@when(parsers.parse('I request statistics for "{team}" in competition "{competition}"'))
def stats_team_competition(engine, context, team, competition):
    context["result"] = engine.team_statistics(team, competition=competition)


# ---------------------------------------------------------------------------
# Then
# ---------------------------------------------------------------------------

@then("I should receive wins, losses, draws, and goals")
def check_record_fields(context):
    result = context["result"]
    for field in ("wins", "losses", "draws", "goals_for", "goals_against"):
        assert field in result
        assert isinstance(result[field], int)


@then("matches should equal wins plus draws plus losses")
def check_record_totals(context):
    result = context["result"]
    assert result["matches"] == result["wins"] + result["draws"] + result["losses"]


@then("matches played should be greater than 0")
def check_matches_positive(context):
    assert context["result"]["matches"] > 0


@then("the win rate should be between 0 and 100")
def check_win_rate(context):
    assert 0.0 <= context["result"]["win_rate"] <= 100.0


@then("goals for plus goals against should be consistent")
def check_goal_difference(context):
    result = context["result"]
    assert result["goal_difference"] == result["goals_for"] - result["goals_against"]
