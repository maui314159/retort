"""
BDD scenarios: team-name, competition and date normalization.

Feature: Data Quality (TASK.md "Data Quality Notes")
  The datasets use different naming conventions and date formats; the
  implementation must normalize them for consistent matching.
"""

from __future__ import annotations

from soccer_mcp.bdd import Scenario, expect, expect_equal
from soccer_mcp.normalize import (
    parse_date_any,
    parse_team_name,
    position_group,
    normalize_competition,
    text_key,
)

FEATURE = "Data Quality: name, competition and date normalization"


def test_state_suffix_is_extracted():
    (
        Scenario(FEATURE, "Team names with a state suffix are decomposed")
        .when("I parse 'Palmeiras-SP'", parsed=lambda ctx: parse_team_name("Palmeiras-SP"))
        .then("the base is 'palmeiras' and the state is 'sp'",
              assertion=lambda ctx: (
                  expect_equal(ctx["parsed"].base, "palmeiras"),
                  expect_equal(ctx["parsed"].state, "sp"),
              ))
        .run()
    )


def test_spaced_state_suffix_is_extracted():
    (
        Scenario(FEATURE, "Cup-file spellings like 'América - MG' are decomposed")
        .when("I parse 'América - MG'", parsed=lambda ctx: parse_team_name("América - MG"))
        .then("accents fold and the state separates",
              assertion=lambda ctx: (
                  expect_equal(ctx["parsed"].base, "america"),
                  expect_equal(ctx["parsed"].state, "mg"),
              ))
        .run()
    )


def test_dot_abbreviations_collapse():
    (
        Scenario(FEATURE, "Dot-separated initials collapse to one token")
        .when("I parse 'C. R. B. - AL'", parsed=lambda ctx: parse_team_name("C. R. B. - AL"))
        .and_("I parse 'A.b.c. - RN'", parsed2=lambda ctx: parse_team_name("A.b.c. - RN"))
        .then("both fold to their undotted spellings",
              assertion=lambda ctx: (
                  expect_equal(ctx["parsed"].base, "crb"),
                  expect_equal(ctx["parsed"].state, "al"),
                  expect_equal(ctx["parsed2"].base, "abc"),
              ))
        .run()
    )


def test_parenthetical_remarks_are_dropped():
    (
        Scenario(FEATURE, "Parenthetical remarks do not pollute the base name")
        .when("I parse a Boavista raw name",
              parsed=lambda ctx: parse_team_name(
                  "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"))
        .then("only the club name and state remain",
              assertion=lambda ctx: (
                  expect_equal(ctx["parsed"].base, "boavista sport club"),
                  expect_equal(ctx["parsed"].state, "rj"),
              ))
        .run()
    )


def test_parenthetical_state_name_is_promoted():
    (
        Scenario(FEATURE, "A state written in parentheses becomes the state")
        .when("I parse the FIFA club 'América FC (Minas Gerais)'",
              parsed=lambda ctx: parse_team_name("América FC (Minas Gerais)"))
        .then("the base is 'america fc' and the state is 'mg'",
              assertion=lambda ctx: (
                  expect_equal(ctx["parsed"].base, "america fc"),
                  expect_equal(ctx["parsed"].state, "mg"),
              ))
        .run()
    )


def test_foreign_country_tags():
    (
        Scenario(FEATURE, "Foreign clubs keep a country tag instead of a state")
        .when("I parse 'Nacional (URU)' and 'Barcelona-EQU'",
              uru=lambda ctx: parse_team_name("Nacional (URU)"),
              equ=lambda ctx: parse_team_name("Barcelona-EQU"))
        .then("the country is extracted, not a Brazilian state",
              assertion=lambda ctx: (
                  expect_equal(ctx["uru"].country, "uru"),
                  expect_equal(ctx["uru"].team_id, "nacional uru"),
                  expect_equal(ctx["equ"].country, "equ"),
                  expect_equal(ctx["equ"].team_id, "barcelona equ"),
              ))
        .run()
    )


def test_iso_and_brazilian_date_formats():
    (
        Scenario(FEATURE, "Multiple date formats are understood")
        .when("I parse '2023-09-24', '2012-05-19 18:30:00', '29/03/2003' and 'NA'",
              iso=lambda ctx: parse_date_any("2023-09-24"),
              isotime=lambda ctx: parse_date_any("2012-05-19 18:30:00"),
              br=lambda ctx: parse_date_any("29/03/2003"),
              na=lambda ctx: parse_date_any("NA"))
        .then("all three parse to the correct dates",
              assertion=lambda ctx: (
                  expect_equal(str(ctx["iso"]), "2023-09-24"),
                  expect_equal(str(ctx["isotime"]), "2012-05-19"),
                  expect_equal(str(ctx["br"]), "2003-03-29"),
              ))
        .and_("the 'NA' sentinel parses to None",
              assertion=lambda ctx: expect(ctx["na"] is None, f"NA parsed to {ctx['na']!r}"))
        .run()
    )


def test_competition_aliases():
    (
        Scenario(FEATURE, "Competition names resolve to canonical ids")
        .when("I normalize several competition spellings",
              brasileirao=lambda ctx: normalize_competition("Brasileirão"),
              seriea=lambda ctx: normalize_competition("serie a"),
              campeonato=lambda ctx: normalize_competition("Campeonato Brasileiro"),
              cup=lambda ctx: normalize_competition("Copa do Brasil"),
              lib=lambda ctx: normalize_competition("Libertadores"),
              serieb=lambda ctx: normalize_competition("Série B"))
        .then("they map onto the right competition ids",
              assertion=lambda ctx: (
                  expect_equal(ctx["brasileirao"], "serie_a"),
                  expect_equal(ctx["seriea"], "serie_a"),
                  expect_equal(ctx["campeonato"], "serie_a"),
                  expect_equal(ctx["cup"], "copa_do_brasil"),
                  expect_equal(ctx["lib"], "libertadores"),
                  expect_equal(ctx["serieb"], "serie_b"),
              ))
        .run()
    )


def test_position_groups():
    (
        Scenario(FEATURE, "FIFA positions map to position groups")
        .when("I group 'ST', 'LW', 'CB' and 'GK'",
              st=lambda ctx: position_group("ST"),
              lw=lambda ctx: position_group("LW"),
              cb=lambda ctx: position_group("CB"),
              gk=lambda ctx: position_group("GK"))
        .then("forwards, defenders and keepers are classified",
              assertion=lambda ctx: (
                  expect_equal(ctx["st"], "FWD"),
                  expect_equal(ctx["lw"], "FWD"),
                  expect_equal(ctx["cb"], "DEF"),
                  expect_equal(ctx["gk"], "GK"),
              ))
        .run()
    )


def test_text_key_folds_accents_and_case():
    (
        Scenario(FEATURE, "Free-text lookup keys fold accents and case")
        .when("I key 'São Paulo' and 'sao paulo'",
              a=lambda ctx: text_key("São Paulo"),
              b=lambda ctx: text_key("sao paulo"))
        .then("both keys are identical",
              assertion=lambda ctx: expect_equal(ctx["a"], ctx["b"]))
        .run()
    )
