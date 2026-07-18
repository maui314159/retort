"""
tests.test_statistical_analysis
==============================

BDD step definitions for ``features/statistical_analysis.feature``.
"""

from __future__ import annotations

from pytest_bdd import scenarios, when, then

scenarios("features/statistical_analysis.feature")


@when('I request average goals for competition "Brasileirão"', target_fixture="state")
def avg_goals_brasileirao(state):
    state["result"] = state["engine"].average_goals(competition="Brasileirão")
    return state


@when("I request the biggest victories", target_fixture="state")
def biggest_victories(state):
    state["result"] = state["engine"].biggest_wins(limit=10)
    return state


@when(
    'I request the best home records in competition "Brasileirão" in season 2019',
    target_fixture="state",
)
def best_home_2019(state):
    state["result"] = state["engine"].best_records(
        competition="Brasileirão", season=2019, venue="home", limit=10
    )
    return state


@when('I search for matches for team "Flamengo-RJ"', target_fixture="state")
def search_flamengo_rj(state):
    state["result"] = state["engine"].search_matches(team="Flamengo-RJ", limit=5)
    return state


@then("I should receive the average goals per match")
def avg_goals_received(state):
    r = state["result"]
    assert "Average goals per match:" in r, f"Expected avg goals: {r[:200]}"


@then("the average should be greater than 2.0")
def avg_gt_2(state):
    r = state["result"]
    import re
    m = re.search(r"Average goals per match: ([\d.]+)", r)
    assert m, f"Expected avg goals number: {r[:200]}"
    assert float(m.group(1)) > 2.0, f"Average {m.group(1)} not > 2.0"


@then("I should receive a list of matches")
def list_of_matches(state):
    r = state["result"]
    assert "Biggest victories" in r, f"Expected biggest victories header: {r[:200]}"


@then("each match should have a score")
def match_has_score(state):
    r = state["result"]
    # each match line has a score pattern like "Team 9-1 Team"
    import re
    scores = re.findall(r"\d+-\d+", r)
    assert scores, f"Expected scores in result: {r[:200]}"


@then("I should receive a ranked list of teams by win rate")
def ranked_teams_win_rate(state):
    r = state["result"]
    assert "1." in r, f"Expected ranked list: {r[:200]}"
    assert "win rate" in r.lower() or "%" in r, f"Expected win rate: {r[:200]}"


@then("the matches should include team \"Flamengo\"")
def matches_include_flamengo(state):
    r = state["result"]
    assert "Flamengo" in r, f"Expected Flamengo in result: {r[:200]}"
