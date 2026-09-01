"""BDD steps for normalization.feature, plus direct unit tests
for the normalization and parsing helpers."""

from __future__ import annotations

from datetime import date

from pytest_bdd import parsers, scenarios, then

from brazilian_soccer.loader import parse_date, parse_int
from brazilian_soccer.normalize import fold, team_key

scenarios("features/normalization.feature")


@then(
    parsers.parse(
        'the names "{a}", "{b}" and "{c}" should resolve to the same team'
    )
)
def three_names_same_team(dataset, a, b, c):
    keys = {team_key(a), team_key(b), team_key(c)}
    assert len(keys) == 1, f"expected one key, got {keys}"


@then(
    parsers.parse('the names "{a}" and "{b}" should resolve to the same team')
)
def two_names_same_team(dataset, a, b):
    assert team_key(a) == team_key(b), f"{a} -> {team_key(a)}, {b} -> {team_key(b)}"


@then(
    parsers.parse(
        'the names "{a}", "{b}", "{c}" and "{d}" should resolve to the same team'
    )
)
def four_names_same_team(dataset, a, b, c, d):
    keys = {team_key(a), team_key(b), team_key(c), team_key(d)}
    assert len(keys) == 1, f"expected one key, got {keys}"


@then(parsers.parse('the name "{name}" should resolve to "{team}"'))
def resolves_to(dataset, name, team):
    info = dataset.registry.get(team_key(name))
    assert info is not None, f"no team for key {team_key(name)!r}"
    assert info.display == team


@then(parsers.parse('the name "{name}" should not resolve to "{team}"'))
def does_not_resolve_to(dataset, name, team):
    assert team_key(name) != team_key(team), (
        f"{name} unexpectedly resolves to {team}"
    )


@then(parsers.parse('the date "{text}" should parse to {expected}'))
def date_parses(text, expected):
    parsed = parse_date(text)
    y, m, d = (int(x) for x in expected.split("-"))
    assert parsed == date(y, m, d)


@then(parsers.parse('the date "{text}" should not parse'))
def date_does_not_parse(text):
    assert parse_date(text) is None


@then("the loaded match count should be lower than the raw CSV row count")
def fewer_than_raw(dataset):
    report = dataset.report
    assert report["unified_matches"] < report["raw_rows_total"]


@then("the 2012 Brasileirão season should have 380 matches")
def season_2012_380(dataset):
    bra = dataset.matches_for_competition("brasileirao")
    count = sum(1 for m in bra if m.season == 2012)
    assert count == 380, f"expected 380, got {count}"


@then(parsers.parse('the folded form of "{text}" should be "{expected}"'))
def folded_form(text, expected):
    assert fold(text) == expected


# ---------------------------------------------------------------------------
# Direct unit tests (no Gherkin)
# ---------------------------------------------------------------------------


def test_parse_int_handles_na_values():
    assert parse_int("NA") is None
    assert parse_int("-") is None
    assert parse_int("") is None
    assert parse_int(None) is None
    assert parse_int("2") == 2
    assert parse_int(2.0) == 2
    assert parse_int("2.0") == 2


def test_parse_date_extra_formats():
    assert parse_date("2023/09/24") == date(2023, 9, 24)
    assert parse_date("29/03/2003 20:00") == date(2003, 3, 29)
    assert parse_date("") is None


def test_team_key_namesakes():
    # Same nickname, different state -> distinct clubs.
    assert team_key("Flamengo - PI") == "flamengopi"
    assert team_key("Flamengo - RJ") == "flamengo"
    assert team_key("Botafogo - PB") == "botafogopb"
    assert team_key("Botafogo SP") == "botafogosp"
    assert team_key("América - RN") == "americarn"
    assert team_key("América - MG") == "americamineiro"


def test_team_key_foreign_country_qualifiers():
    assert team_key("Nacional (URU)") == "nacionaluru"
    assert team_key("Nacional-URU") == "nacionaluru"
    assert team_key("Nacional (PAR)") == "nacionalpar"
    assert team_key("Barcelona-EQU") == "barcelonaequ"
    assert team_key("Guaraní (PAR)") == "guaranipar"
    assert team_key("Guarani") == "guarani"  # Brazilian namesake stays separate


def test_team_key_spelling_drift():
    assert team_key("Atletico-MG") == team_key("Atlético Mineiro") == "atleticomineiro"
    assert team_key("Athletico") == team_key("Atletico-PR") == "atleticoparanaense"
    assert team_key("Vasco") == team_key("Vasco da Gama-RJ") == "vascodagama"
    assert team_key("Sport") == team_key("Sport Club do Recife") == "sportrecife"


def test_team_key_empty_and_edge_cases():
    assert team_key("") == ""
    assert team_key("   ") == ""
    assert team_key("CSA") == "csa"
    assert team_key("LDU") == "ldu"  # all-caps name without separator is preserved
    # Unclaimed names keep their state suffix, so namesakes never merge.
    assert team_key("ASA AL") == "asaal"
