"""
tests.test_team_queries
======================

BDD step definitions for ``features/team_queries.feature``.
"""

from __future__ import annotations

from pytest_bdd import scenarios, when, then

scenarios("features/team_queries.feature")


@when('I request statistics for "Corinthians" in season 2022', target_fixture="state")
def corinthians_2022(state):
    state["result"] = state["engine"].team_statistics("Corinthians", season=2022)
    return state


@when(
    'I request home statistics for "Corinthians" in season 2022 in competition "Brasileirão"',
    target_fixture="state",
)
def corinthians_home_2022(state):
    state["result"] = state["engine"].team_statistics(
        "Corinthians", season=2022, competition="Brasileirão", venue="home"
    )
    return state


@when('I compare "Flamengo" and "Fluminense"', target_fixture="state")
def compare_flamengo_fluminense(state):
    state["result"] = state["engine"].compare_teams("Flamengo", "Fluminense")
    return state


@when('I request competitions for "Palmeiras"', target_fixture="state")
def palmeiras_competitions(state):
    state["result"] = state["engine"].competitions_for_team("Palmeiras")
    return state


@then("I should receive wins, losses, draws, and goals")
def stats_have_wld_gf(state):
    r = state["result"]
    assert "Wins:" in r and "Draws:" in r and "Losses:" in r, f"Missing W/D/L: {r[:200]}"
    assert "Goals For:" in r, f"Missing goals: {r[:200]}"


@then("I should receive home wins, draws, losses, and goals")
def home_stats_have_fields(state):
    r = state["result"]
    assert "Wins:" in r and "Draws:" in r and "Losses:" in r
    assert "Goals For:" in r


@then("the win rate should be a percentage")
def win_rate_is_percentage(state):
    r = state["result"]
    assert "%" in r, f"Expected win rate percentage: {r[:200]}"


@then("I should receive head-to-head wins for both teams")
def h2h_wins_both(state):
    r = state["result"]
    assert "wins" in r, f"Expected wins in h2h: {r[:200]}"


@then("I should see at least 2 competitions")
def at_least_2_comps(state):
    r = state["result"]
    # count lines that look like competition entries
    lines = [l.strip() for l in r.split("\n") if l.strip() and not l.startswith("Competitions")]
    assert len(lines) >= 2, f"Expected >=2 competitions: {r[:200]}"
