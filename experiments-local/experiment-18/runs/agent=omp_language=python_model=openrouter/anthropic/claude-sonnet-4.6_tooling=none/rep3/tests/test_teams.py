"""
================================================================================
tests.test_teams
================================================================================
Context:
    BDD step definitions for tests/features/teams.feature. Covers team-record
    aggregation (W/D/L + goals), home-only records, head-to-head consistency,
    and the same-base-name disambiguation invariant (Atletico-MG != Atletico-GO).
================================================================================
"""

from pytest_bdd import parsers, scenarios, then, when

scenarios("features/teams.feature")


@when(parsers.parse('I request statistics for "{team}" in season {season:d}'))
def _stats(graph, context, team, season):
    context["res"] = graph.team_stats(team, season=season, competition="Brasileirao")


@when(parsers.parse('I request the home record for "{team}" in season {season:d}'))
def _home(graph, context, team, season):
    context["res"] = graph.team_stats(
        team, season=season, competition="Brasileirao", home_only=True
    )


@when(parsers.parse('I compare "{a}" and "{b}" head-to-head'))
def _compare(graph, context, a, b):
    context["h2h"] = graph.head_to_head(a, b)


@when(parsers.parse('I resolve the teams "{a}" and "{b}"'))
def _resolve_two(graph, context, a, b):
    context["ka"] = graph.resolve_team(a)
    context["kb"] = graph.resolve_team(b)


@then("I should receive wins, losses, draws, and goals")
def _have_record(context):
    assert context["res"] is not None
    _, rec = context["res"]
    assert rec.matches > 0
    assert rec.goals_for >= 0 and rec.goals_against >= 0


@then("the number of matches should equal wins plus draws plus losses")
def _record_sums(context):
    _, rec = context["res"]
    assert rec.matches == rec.wins + rec.draws + rec.losses


@then("the win rate should be between 0 and 1")
def _winrate(context):
    _, rec = context["res"]
    assert 0.0 <= rec.win_rate <= 1.0


@then("goals for and goals against should be non-negative")
def _goals_nonneg(context):
    _, rec = context["res"]
    assert rec.goals_for >= 0 and rec.goals_against >= 0


@then("wins, draws and goals should be consistent with the meetings")
def _h2h_consistent(context):
    h = context["h2h"]
    decided = [m for m in h["meetings"] if m.home_goal is not None]
    assert h["a_wins"] + h["b_wins"] + h["draws"] == len(decided)
    assert h["a_goals"] >= 0 and h["b_goals"] >= 0


@then("they should resolve to different teams")
def _different(context):
    assert context["ka"] is not None and context["kb"] is not None
    assert context["ka"] != context["kb"]
