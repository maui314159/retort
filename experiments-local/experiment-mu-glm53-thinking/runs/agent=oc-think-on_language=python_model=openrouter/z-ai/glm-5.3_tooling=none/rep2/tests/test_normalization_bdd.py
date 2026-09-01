"""BDD scenarios for name, date and competition normalisation.

Feature: Normalisation
  The datasets spell the same club in many ways, use three date formats
  and label competitions differently.  The implementation must normalise
  team names, parse every date format and map competition labels.
"""

from __future__ import annotations

from datetime import date

from brazilian_soccer_mcp.normalize import (
    normalize_competition,
    normalize_team_id,
    parse_date,
    team_display_name,
)


def test_state_suffixes_are_stripped():
    """Scenario: Team names with state suffixes
    Given datasets spell clubs with and without state suffixes
    When "Palmeiras-SP", "Palmeiras" and "Palmeiras - SP" are normalised
    Then all three resolve to the same canonical id
    """
    # Given
    variants = ["Palmeiras-SP", "Palmeiras", "Palmeiras - SP", "palmeiras sp"]

    # When
    ids = {normalize_team_id(v) for v in variants}

    # Then
    assert ids == {"palmeiras"}


def test_accents_and_case_do_not_matter():
    """Scenario: Accented and unaccented spellings
    Given some datasets drop accents ("Atletico-MG", "Sao Paulo")
    When normalised
    Then they match the accented spellings used elsewhere
    """
    # Given
    pairs = [
        ("Atletico-MG", "Atlético-MG"),
        ("Sao Paulo", "São Paulo"),
        ("Goias", "Goiás"),
        ("Gremio-RS", "Grêmio"),
        ("Criciuma-SC", "Criciúma"),
    ]

    # When / Then
    for unaccented, accented in pairs:
        assert normalize_team_id(unaccented) == normalize_team_id(accented)


def test_athletico_pr_spellings_unify():
    """Scenario: Athletico Paranaense naming chaos
    Given the club is spelled "Atletico-PR", "Athletico-PR",
    "Atlético Paranaense", "Athletico Paranaense" and bare "Athletico"
    When normalised
    Then every spelling maps to the same canonical id
    """
    # Given
    variants = [
        "Atletico-PR",
        "Athletico-PR",
        "Atlético Paranaense",
        "Athletico Paranaense",
        "Atletico Paranaense",
        "Athletico",
        "Athletico - PR",
    ]

    # When
    ids = {normalize_team_id(v) for v in variants}

    # Then
    assert ids == {"athletico-pr"}


def test_ambiguous_clubs_keep_their_state_suffix():
    """Scenario: Same base name, different clubs
    Given "Botafogo-PB" and "Botafogo-RJ" are different clubs
    When normalised
    Then they stay distinct, while bare "Botafogo" means the Rio club
    """
    # Given
    botafogo_rj = ["Botafogo-RJ", "Botafogo RJ", "Botafogo", "Botafogo - RJ"]
    botafogo_pb = ["Botafogo-PB", "Botafogo PB"]

    # When
    rj_ids = {normalize_team_id(v) for v in botafogo_rj}
    pb_ids = {normalize_team_id(v) for v in botafogo_pb}

    # Then
    assert rj_ids == {"botafogo-rj"}
    assert pb_ids == {"botafogo-pb"}
    assert rj_ids != pb_ids


def test_fifa_full_names_resolve():
    """Scenario: FIFA dataset uses full club names
    Given FIFA spells clubs like "América FC (Minas Gerais)",
    "Sport Club do Recife" and "Atlético Mineiro"
    When normalised
    Then they map to the same ids as the match datasets
    """
    # Given
    pairs = [
        ("América FC (Minas Gerais)", "América-MG"),
        ("Sport Club do Recife", "Sport-PE"),
        ("Atlético Mineiro", "Atlético-MG"),
        ("Ceará Sporting Club", "Ceará-CE"),
        ("Atlético Paranaense", "Athletico-PR"),
    ]

    # When / Then
    for fifa_name, match_name in pairs:
        assert normalize_team_id(fifa_name) == normalize_team_id(match_name)


def test_libertadores_country_tags():
    """Scenario: Libertadores foreign clubs carry country tags
    Given Libertadores spells clubs "Nacional (URU)", "Nacional-URU"
    and "Barcelona-EQU"
    When normalised
    Then bracket and hyphen tags produce identical ids
    """
    # Given
    pairs = [
        ("Nacional (URU)", "Nacional-URU"),
        ("Guaraní (PAR)", "Guaraní-PAR"),
    ]

    # When / Then
    for bracketed, hyphenated in pairs:
        assert normalize_team_id(bracketed) == normalize_team_id(hyphenated)
    assert normalize_team_id("Barcelona-EQU") == "barcelona-equ"
    assert normalize_team_id("Nacional (URU)") != normalize_team_id("Nacional (PAR)")


def test_display_names_restore_accents():
    """Scenario: Canonical ids become readable names
    Given canonical ids are lowercase and unaccented
    When rendered for display
    Then proper Portuguese names come back
    """
    # Given
    ids = ["flamengo", "sao-paulo", "gremio", "athletico-pr", "goias"]

    # When
    names = {team_display_name(i) for i in ids}

    # Then
    assert names == {"Flamengo", "São Paulo", "Grêmio", "Athletico Paranaense", "Goiás"}


def test_all_three_date_formats_parse():
    """Scenario: Date formats
    Given matches arrive as ISO, ISO-with-time and Brazilian dates
    When parsed
    Then all three yield the same date object and NA yields None
    """
    # Given
    iso = "2023-09-24"
    iso_time = "2012-05-19 18:30:00"
    brazilian = "29/03/2003"

    # When
    d1 = parse_date(iso)
    d2 = parse_date(iso_time)
    d3 = parse_date(brazilian)

    # Then
    assert d1 == date(2023, 9, 24)
    assert d2 == date(2012, 5, 19)
    assert d3 == date(2003, 3, 29)
    assert parse_date("NA") is None
    assert parse_date("") is None
    assert parse_date("-") is None


def test_competition_labels_normalise():
    """Scenario: Competition names
    Given users type "Serie A", "brasileirao" and "Libertadores"
    When normalised
    Then the canonical competition names come back
    """
    # Given
    queries = ["Serie A", "serie a", "brasileirao", "Série B", "copa do brasil", "libertadores"]

    # When
    results = [normalize_competition(q) for q in queries]

    # Then
    assert results == [
        "Brasileirão Série A",
        "Brasileirão Série A",
        "Brasileirão Série A",
        "Brasileirão Série B",
        "Copa do Brasil",
        "Copa Libertadores",
    ]
