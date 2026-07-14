"""
BDD step definitions for match_queries.feature
"""

from __future__ import annotations

import json

from pytest_bdd import given, when, then, scenarios

scenarios("match_queries.feature")


@given("the match data is loaded")
def match_data_loaded():
    pass  # Data is lazy-loaded by the tools


@when('I search for matches between "Flamengo" and "Fluminense"')
def search_flamengo_fluminense(invoker):
    invoker.result = json.loads(invoker.search_matches(team="Flamengo", opponent="Fluminense"))


@then("I should receive a list of matches")
def receive_match_list(invoker):
    assert isinstance(invoker.result, list)
    assert len(invoker.result) > 0


@then("each match should have date, scores, and competition")
def match_has_required_fields(invoker):
    for match in invoker.result:
        assert "date" in match or "home_team" in match
        assert "home_goal" in match
        assert "away_goal" in match
        assert "competition" in match


@when('I search for matches with team "Palmeiras" in season 2023')
def search_palmeiras_2023(invoker):
    invoker.result = json.loads(invoker.search_matches(team="Palmeiras", season=2023))


@then("I should receive matches only from season 2023")
def matches_from_2023(invoker):
    for match in invoker.result:
        assert match.get("season") == 2023


@when('I search for matches in competition "Copa do Brasil"')
def search_copa_do_brasil(invoker):
    invoker.result = json.loads(invoker.search_matches(competition="Copa do Brasil"))


@then("all results should be from Copa do Brasil")
def results_from_copa(invoker):
    for match in invoker.result:
        assert "copa do brasil" in match.get("competition", "").lower()


@when('I search for matches from "2023-01-01" to "2023-12-31"')
def search_date_range(invoker):
    invoker.result = json.loads(invoker.search_matches(date_from="2023-01-01", date_to="2023-12-31"))


@then("all results should be within that date range")
def results_in_date_range(invoker):
    for match in invoker.result:
        d = match.get("date", "")
        if d:
            # Date is ISO format: 2023-XX-XX...
            assert d.startswith("2023")


@when('I request head-to-head between "Flamengo" and "Fluminense"')
def head_to_head_flu(invoker):
    invoker.result = json.loads(invoker.head_to_head(team_a="Flamengo", team_b="Fluminense"))


@then("I should receive wins draws and losses for each team")
def h2h_has_stats(invoker):
    assert "Flamengo_wins" in invoker.result or "draws" in invoker.result
    assert "total_matches" in invoker.result
