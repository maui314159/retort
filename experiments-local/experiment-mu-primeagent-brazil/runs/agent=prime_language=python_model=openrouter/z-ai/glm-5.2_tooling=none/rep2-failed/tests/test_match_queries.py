"""
Context block
=============
Brazilian Soccer MCP Server - BDD Step Definitions: Match Queries
"""

from pytest_bdd import scenarios, given, when, then, parsers
import pytest

scenarios("features/match_queries.feature")


@pytest.fixture
def ctx():
    return {}


@given("the match data is loaded", target_fixture="match_data")
def match_data_loaded(engine):
    return engine


@when('I search for matches between "Flamengo" and "Fluminense"', target_fixture="matches")
def search_between(match_data, ctx):
    ctx["matches"] = match_data.find_matches(team="Flamengo",
                                             opponent="Fluminense", limit=None)
    return ctx["matches"]


@when(parsers.parse('I search for matches for team "{team}" in season {season:d}'),
      target_fixture="matches")
def search_team_season(match_data, ctx, team, season):
    ctx["matches"] = match_data.find_matches(team=team, season=season, limit=None)
    return ctx["matches"]


@when(parsers.parse('I search for matches in competition "{competition}"'),
      target_fixture="matches")
def search_competition(match_data, ctx, competition):
    ctx["matches"] = match_data.find_matches(competition=competition, limit=None)
    return ctx["matches"]


@when('I ask for the last match between "Flamengo" and "Corinthians"',
      target_fixture="last_match")
def last_match(match_data, ctx):
    ctx["last_match"] = match_data.last_match_between("Flamengo", "Corinthians")
    return ctx["last_match"]


@then("I should receive a list of matches")
def assert_list(matches):
    assert isinstance(matches, list)
    assert len(matches) > 0


@then("each match should have a date, scores and a competition")
def assert_match_fields(matches):
    for m in matches:
        assert "date" in m
        assert "home_goal" in m and "away_goal" in m
        assert "competition" in m


@then("I should receive at least one match")
def assert_at_least_one(matches):
    assert len(matches) >= 1


@then(parsers.parse("every match should be from season {season:d}"))
def assert_season(matches, season):
    assert all(int(m["season"]) == season for m in matches)


@then(parsers.parse('every match should involve {team}'))
def assert_involves(matches, team):
    from brazilian_soccer_mcp.normalizer import display_name
    dn = display_name(team)
    for m in matches:
        assert dn in (m["home_team"], m["away_team"]), (m, dn)


@then("I should receive matches")
def assert_has_matches(matches):
    assert len(matches) > 0


@then(parsers.parse('every match should belong to the {competition} competition'))
def assert_competition(matches, competition):
    allowed = {"Copa do Brasil": ["Copa do Brasil"]}
    names = allowed.get(competition, [competition])
    assert all(m["competition"] in names for m in matches)


@then("I should receive a single match with a date and a score")
def assert_last_match(last_match):
    assert last_match is not None
    assert last_match["date"] is not None
    assert last_match["home_goal"] is not None
    assert last_match["away_goal"] is not None
