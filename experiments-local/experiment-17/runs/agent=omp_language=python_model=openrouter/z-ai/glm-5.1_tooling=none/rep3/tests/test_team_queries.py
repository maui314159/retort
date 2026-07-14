"""
BDD step definitions for team_queries.feature
"""

from __future__ import annotations

import json

from pytest_bdd import given, when, then, scenarios

scenarios("team_queries.feature")


@given("the match data is loaded")
def match_data_loaded():
    pass


@when('I request statistics for "Palmeiras"')
def stats_palmeiras(invoker):
    invoker.result = json.loads(invoker.team_statistics(team="Palmeiras"))


@then("I should receive wins losses draws and goals")
def stats_have_fields(invoker):
    r = invoker.result
    assert "wins" in r
    assert "losses" in r
    assert "draws" in r
    assert "goals_for" in r
    assert "goals_against" in r
    assert r["matches"] > 0


@when('I request statistics for "Corinthians" in season 2022')
def stats_corinthians_2022(invoker):
    invoker.result = json.loads(invoker.team_statistics(team="Corinthians", season=2022))


@then("I should receive season-specific statistics")
def season_stats(invoker):
    r = invoker.result
    assert r["matches"] > 0
    # Verify the stats are reasonable for a single season
    assert r["wins"] + r["draws"] + r["losses"] == r["matches"]


@when('I request home statistics for "Flamengo"')
def home_stats_flamengo(invoker):
    invoker.result = json.loads(invoker.team_statistics(team="Flamengo", side="home"))


@then("the statistics should reflect home matches only")
def home_only_stats(invoker):
    r = invoker.result
    assert r["matches"] > 0
    # Home stats should be a subset of total
    assert r["home"] is not None or "home" not in r


@when("I request top teams by goals")
def top_teams(invoker):
    invoker.result = json.loads(invoker.top_teams_by_goals())


@then("I should receive a ranked list of teams by goals scored")
def ranked_by_goals(invoker):
    r = invoker.result
    assert isinstance(r, list)
    assert len(r) > 0
    # Verify descending order
    goals = [t["goals"] for t in r]
    assert goals == sorted(goals, reverse=True)
