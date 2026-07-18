"""
tests.test_competition_queries
=============================

BDD step definitions for ``features/competition_queries.feature``.
"""

from __future__ import annotations

from pytest_bdd import scenarios, when, then

scenarios("features/competition_queries.feature")


@when('I request standings for competition "Brasileirão" in season 2019', target_fixture="state")
def standings_brasileirao_2019(state):
    state["result"] = state["engine"].standings("Brasileirão", 2019, top_n=20)
    return state


@when('I request information for competition "Libertadores"', target_fixture="state")
def info_libertadores(state):
    state["result"] = state["engine"].competition_info("Libertadores")
    return state


@when('I request standings for competition "Champions League" in season 2019', target_fixture="state")
def standings_champions_league(state):
    state["result"] = state["engine"].standings("Champions League", 2019)
    return state


@then("I should receive a ranked table of teams")
def ranked_table(state):
    r = state["result"]
    assert "1." in r and "2." in r, f"Expected ranked table: {r[:200]}"
    assert "pts" in r, f"Expected points: {r[:200]}"


@then("the first team should be marked as champion")
def first_is_champion(state):
    r = state["result"]
    assert "Champion" in r, f"Expected champion marker: {r[:200]}"


@then('the champion should be "Flamengo"')
def champion_is_flamengo(state):
    r = state["result"]
    # the champion line: "1. Flamengo - ... - Champion"
    import re
    m = re.search(r"1\.\s+(\S+).*Champion", r)
    assert m, f"Expected champion line: {r[:300]}"
    assert "Flamengo" in m.group(1), f"Expected Flamengo as champion, got {m.group(1)}"


@then("I should receive seasons and match count")
def comp_has_seasons_matches(state):
    r = state["result"]
    assert "Seasons:" in r, f"Expected seasons: {r[:200]}"
    assert "Total matches:" in r, f"Expected match count: {r[:200]}"


@then("the match count should be at least 1000")
def match_count_1000(state):
    r = state["result"]
    import re
    m = re.search(r"Total matches: (\d+)", r)
    assert m, f"Expected match count: {r[:200]}"
    assert int(m.group(1)) >= 1000, f"Expected >=1000 matches, got {m.group(1)}"
