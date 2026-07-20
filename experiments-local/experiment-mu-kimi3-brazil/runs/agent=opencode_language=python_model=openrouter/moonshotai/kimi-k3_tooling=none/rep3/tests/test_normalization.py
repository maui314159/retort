"""Step definitions for normalization.feature (data quality + cross-file)."""

from __future__ import annotations

from pytest_bdd import parsers, scenarios, then, when

import query_engine as qe
from soccer_data import normalize_team, parse_date

scenarios("features/normalization.feature")


@then(parsers.parse('the team names "{n1}", "{n2}" and "{n3}" should all '
                    'normalise to "{key}"'))
def check_three_names(n1, n2, n3, key):
    assert normalize_team(n1) == key
    assert normalize_team(n2) == key
    assert normalize_team(n3) == key


@then(parsers.parse('the team names "{n1}" and "{n2}" should both normalise '
                    'to "{key}"'))
@then(parsers.parse('the team names "{n1}" and "{n2}" should all normalise '
                    'to "{key}"'))
def check_two_names(n1, n2, key):
    assert normalize_team(n1) == key
    assert normalize_team(n2) == key


@then(parsers.parse('the team name "{name}" should normalise to "{key}"'))
def check_one_name(name, key):
    assert normalize_team(name) == key


@then(parsers.parse('the date "{text}" should parse to year {year:d} month '
                    '{month:d} day {day:d}'))
def check_date(text, year, month, day):
    parsed = parse_date(text)
    assert parsed.year == year
    assert parsed.month == month
    assert parsed.day == day


@then(parsers.parse('matches from source "{source}" should be present'))
def check_source(store, source):
    assert (store.played_matches.source == source).any()


@then(parsers.parse("the player table should contain more than {count:d} "
                    "players"))
def check_player_count(store, count):
    assert len(store.players) > count


@when(parsers.parse('I search for matches of "{team}" in competition '
                    '"{comp}" and season {season:d}'))
def cross_matches(store, context, team, comp, season):
    context["matches"] = qe.find_matches(team=team, competition=comp,
                                         season=season, limit=100,
                                         store=store)


@then(parsers.parse("the club search should return at least {count:d} "
                    "players"))
def check_cross_players(context, count):
    assert context["result"]["total"] >= count


@then(parsers.parse("the match search should return {count:d} matches"))
def check_cross_matches(context, count):
    assert context["matches"]["total"] == count
