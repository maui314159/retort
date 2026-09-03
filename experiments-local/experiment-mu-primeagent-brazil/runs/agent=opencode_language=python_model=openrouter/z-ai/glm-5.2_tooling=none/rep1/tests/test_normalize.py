"""BDD tests for name, date and competition normalisation.

Feature: Name Normalisation

  Scenario: Cross-file team name variants collapse onto one canonical key
    Given the messy team-name variants present across the Kaggle CSVs
    When they are normalised
    Then "Palmeiras-SP", "Palmeiras" and "Palmeiras-SP" all map to "palmeiras"
    And "Atlético-MG" and "Atletico Mineiro" both map to "atletico mg"
    And distinct same-named clubs keep their state ("Botafogo-RJ" != "Botafogo-SP")

  Scenario: Dates are parsed from every source format
    Given ISO, ISO-with-time and Brazilian (DD/MM/YYYY) date strings
    When they are parsed
    Then each yields the correct calendar date
"""

from __future__ import annotations

from datetime import date

from brazilian_soccer_mcp.normalize import (
    competition_matches,
    normalize_team_name,
    parse_date,
)


def test_unambiguous_clubs_drop_state_suffix():
    assert normalize_team_name("Palmeiras-SP") == "palmeiras"
    assert normalize_team_name("Palmeiras") == "palmeiras"
    assert normalize_team_name("Flamengo-RJ") == "flamengo"
    assert normalize_team_name("Flamengo") == "flamengo"
    assert normalize_team_name("São Paulo-SP") == "sao paulo"
    assert normalize_team_name("Sao Paulo") == "sao paulo"
    assert normalize_team_name("Grêmio-RS") == "gremio"
    assert normalize_team_name("Gremio") == "gremio"


def test_ambiguous_clubs_bridged_via_full_name():
    assert normalize_team_name("Atlético-MG") == "atletico mg"
    assert normalize_team_name("Atletico Mineiro") == "atletico mg"
    assert normalize_team_name("América-MG") == "america mg"
    assert normalize_team_name("América Mineiro") == "america mg"
    assert normalize_team_name("Athletico-PR") == "athletico pr"
    assert normalize_team_name("Atletico Paranaense") == "athletico pr"


def test_vasco_and_sport_full_name_bridging():
    assert normalize_team_name("Vasco") == "vasco da gama"
    assert normalize_team_name("Vasco da Gama") == "vasco da gama"
    assert normalize_team_name("Vasco Da Gama RJ") == "vasco da gama"
    assert normalize_team_name("Sport-PE") == "sport"
    assert normalize_team_name("Sport Club do Recife") == "sport"
    assert normalize_team_name("EC Bahia") == "bahia"
    assert normalize_team_name("Esporte Clube Bahia") == "bahia"


def test_distinct_same_named_clubs_stay_distinct():
    assert normalize_team_name("Botafogo-RJ") == "botafogo"
    assert normalize_team_name("Botafogo-SP") == "botafogo sp"
    assert normalize_team_name("Botafogo PB") == "botafogo pb"
    assert normalize_team_name("Atlético-MG") != normalize_team_name("Atlético-GO")
    assert normalize_team_name("Atlético-GO") == "atletico go"
    assert normalize_team_name("América-MG") != normalize_team_name("América-RN")


def test_parenthetical_notes_and_club_tokens_stripped():
    assert "antigo" not in normalize_team_name(
        "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ")
    assert normalize_team_name("São Paulo FC") == "sao paulo"
    assert normalize_team_name("Fortaleza FC") == "fortaleza"


def test_empty_and_none_inputs():
    assert normalize_team_name(None) == ""
    assert normalize_team_name("") == ""

def test_competition_substring_matching():
    assert competition_matches("Brasileirão", "Brasileirão Serie A")
    assert competition_matches("serie a", "Brasileirão Serie A")
    assert competition_matches("Brasileirão Serie A", "Brasileirão Serie A")
    assert not competition_matches("Brasileirão Serie A", "Brasileirão Serie B")
    assert not competition_matches("serie a", "Brasileirão Serie B")
    assert competition_matches("Libertadores", "Copa Libertadores")
    assert competition_matches("Copa do Brasil", "Copa do Brasil")
    assert competition_matches(None, "Anything") is True


def test_parse_iso_date():
    assert parse_date("2023-09-24") == date(2023, 9, 24)


def test_parse_iso_datetime():
    assert parse_date("2012-05-19 18:30:00") == date(2012, 5, 19)


def test_parse_brazilian_date():
    assert parse_date("29/03/2003") == date(2003, 3, 29)


def test_parse_invalid_and_empty():
    assert parse_date(None) is None
    assert parse_date("") is None
    assert parse_date("not a date") is None
