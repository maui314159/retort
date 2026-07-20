"""Step definitions for data_quality.feature."""

from __future__ import annotations

import datetime as dt

from pytest_bdd import parsers, then, when, scenarios

from brazilian_soccer_mcp.normalization import parse_date, team_key

scenarios("features/data_quality.feature")


# ---------------------------------------------------------------------------
# When
# ---------------------------------------------------------------------------

@when(parsers.parse('I search matches for team "{team}" in season {season:d}'))
def search_team_season(engine, context, team, season):
    context["result"] = engine.search_matches(team=team, season=season)


# ---------------------------------------------------------------------------
# Then: name normalization
# ---------------------------------------------------------------------------

@then(parsers.parse('"{name_a}" and "{name_b}" should resolve to the same team'))
def check_same_team(name_a, name_b):
    assert team_key(name_a) == team_key(name_b)
    assert team_key(name_a) != ""


@then(parsers.parse('"{name_a}" and "{name_b}" should resolve to different teams'))
def check_different_teams(name_a, name_b):
    assert team_key(name_a) != team_key(name_b)


# ---------------------------------------------------------------------------
# Then: date parsing
# ---------------------------------------------------------------------------

@then(parsers.parse('"{raw}" should parse to the date "{expected}"'))
def check_date_parse(raw, expected):
    assert parse_date(raw) == dt.date.fromisoformat(expected)


# ---------------------------------------------------------------------------
# Then: matches / coverage
# ---------------------------------------------------------------------------

@then("I should receive a list of matches")
def check_match_list(context):
    result = context["result"]
    assert result["total"] > 0
    assert result["matches"]


@then(parsers.parse("the dataset overview should list {count:d} match sources"))
def check_source_count(engine, count):
    overview = engine.overview()
    assert len(overview["sources"]) == count
    assert overview["total_matches"] > 15000


@then(parsers.parse("the player table should have more than {count:d} rows"))
def check_player_rows(engine, count):
    assert engine.overview()["total_players"] > count
