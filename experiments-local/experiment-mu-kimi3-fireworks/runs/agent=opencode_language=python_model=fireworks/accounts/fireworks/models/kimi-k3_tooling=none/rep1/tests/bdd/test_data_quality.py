"""BDD step definitions for data_quality.feature."""

from __future__ import annotations

from pytest_bdd import parsers, scenarios, then, when

from soccer_mcp.normalize import (
    canonical_competition,
    canonical_team,
    parse_date,
)

scenarios("../features/data_quality.feature")


@when(parsers.parse("I normalize the team name {raw}"))
def normalize_team(context, raw):
    context["canonical"] = canonical_team(raw)


@when(parsers.parse("I parse the date {raw}"))
def parse_dt(context, raw):
    context["parsed"] = parse_date(raw)


@then(parsers.parse("the canonical team should be {expected}"))
def canonical_is(context, expected):
    assert context["canonical"] == expected


@then(parsers.parse("the parsed date should be {expected}"))
def parsed_is(context, expected):
    assert context["parsed"].strftime("%Y-%m-%d") == expected


@then(parsers.parse('the store should contain teams "{t1}", "{t2}" and "{t3}"'))
def store_contains(store, t1, t2, t3):
    for team in (t1, t2, t3):
        assert team in store.teams


@then(parsers.parse('"{raw}" should resolve to the "{key}" competition'))
def competition_resolves(raw, key):
    assert canonical_competition(raw) == key
