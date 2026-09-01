"""BDD step definitions for the Data Quality feature."""

from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, when, then

from brazilian_soccer.normalize import parse_date

scenarios("../features/data_quality.feature")


@given("the team registry is finalized")
def registry_ready(store):
    return store.registry


@given(parsers.parse('a Brazilian formatted date "{raw}"'), target_fixture="date_raw")
def given_brazilian_date(raw):
    return raw


@given(parsers.parse('an ISO datetime "{raw}"'), target_fixture="date_raw")
def given_iso_datetime(raw):
    return raw


@given("the store is loaded")
def loaded_store(store):
    return store


@when(parsers.parse('I resolve "{name_a}" and "{name_b}"'), target_fixture="resolved")
def resolve_two(store, name_a, name_b):
    return {"a": store.resolve_team(name_a), "b": store.resolve_team(name_b)}


@when("I check the display names", target_fixture="checked")
def check_displays(store):
    return {"displays": set(store.registry.display_names().values())}


@when(parsers.parse('I query the FIFA club "{club}"'), target_fixture="queried")
def query_fifa_club(store, club):
    key = store.resolve_team(club)
    return {
        "key": key,
        "match_count": len(store.matches_by_team.get(key, [])),
        "player_count": len(store.players_by_club.get(key, [])),
    }


@when("I parse the date", target_fixture="parsed")
def parse_the_date(date_raw):
    return {"date": parse_date(date_raw)}


@then("both names should resolve to the same club")
def assert_same_club(resolved):
    assert resolved["a"] == resolved["b"]


@then("the names should resolve to different clubs")
def assert_different_clubs(resolved):
    assert resolved["a"] != resolved["b"]


@then(parsers.parse("the parsed date should be {expected}"))
def assert_parsed_date(parsed, expected):
    assert str(parsed["date"]) == expected


@then(parsers.parse('the names "{n1}", "{n2}" and "{n3}" should be present'))
def assert_utf8_names(checked, n1, n2, n3):
    for name in (n1, n2, n3):
        assert name in checked["displays"], f"{name} not in display names"


@then("the players should link to the same club that appears in match data")
def assert_cross_file_link(queried):
    assert queried["player_count"] > 0, "expected FIFA players for the club"
    assert queried["match_count"] > 0, "expected matches for the same club key"
