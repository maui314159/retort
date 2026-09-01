"""Feature: Data normalization
  The datasets spell one club many ways and store dates and numbers in
  mixed formats. Normalization must fold every spelling of a club into one
  stable identity, keep genuinely different clubs apart, and parse every
  date format used across the files.
"""

from datetime import date

import pytest

from brazilian_soccer.normalize import parse_date, parse_int, split_team


class TestTeamNameNormalization:
    def test_state_suffix_and_plain_spellings_are_the_same_club(self):
        # Given the suffix, plain and prefixed spellings of Palmeiras
        spellings = ["Palmeiras-SP", "Palmeiras", "palmeiras", "SE Palmeiras"]
        # When each is reduced to its (base, qualifier) identity
        identities = {split_team(spelling) for spelling in spellings}
        # Then they all denote the same club
        assert identities == {("palmeiras", "sp")}

    def test_accented_and_unaccented_spellings_are_the_same_club(self):
        # Given "Grêmio", "Gremio-RS" and "gremio"
        spellings = ["Grêmio", "Gremio-RS", "gremio"]
        # When normalized
        identities = {split_team(spelling) for spelling in spellings}
        # Then they denote the same club
        assert identities == {("gremio", "rs")}

    def test_full_official_names_map_to_common_names(self):
        # Given official club names used in prose and the FIFA database
        cases = {
            "Sport Club Corinthians Paulista": ("corinthians", "sp"),
            "Sociedade Esportiva Palmeiras": ("palmeiras", "sp"),
            "Clube de Regatas do Flamengo": ("flamengo", "rj"),
            "São Paulo FC": ("sao paulo", "sp"),
            "Atlético Mineiro": ("atletico", "mg"),
            "Atlético Paranaense": ("atletico", "pr"),
            "Athletico Paranaense": ("atletico", "pr"),
            "Fortaleza Esporte Clube": ("fortaleza", "ce"),
            "Ceará Sporting Club": ("ceara", "ce"),
            "Sport Club do Recife": ("sport", "pe"),
        }
        # When split into identity pairs
        # Then each official name matches its common club identity
        for raw, expected in cases.items():
            assert split_team(raw) == expected, raw

    def test_athletico_and_atletico_pr_spellings_join(self):
        # Given the 2019 rebrand spelling and the historical spelling
        spellings = ["Athletico-PR", "Atlético-PR", "Atletico-PR", "Athletico"]
        # When normalized
        identities = {split_team(spelling) for spelling in spellings}
        # Then they are one club
        assert identities == {("atletico", "pr")}

    def test_vasco_long_name_joins_short_spelling(self):
        assert split_team("Vasco da Gama-RJ") == ("vasco", "rj")
        assert split_team("Vasco") == ("vasco", "rj")

    def test_same_base_different_state_stay_distinct(self):
        # Given clubs whose names differ only by state
        pairs = [
            ("America-MG", "America-RN"),
            ("Botafogo-RJ", "Botafogo-PB"),
            ("Vitória-BA", "Vitória-ES"),
            ("Atlético-MG", "Atlético-GO"),
        ]
        # When normalized
        # Then each pair produces two different identities
        for left, right in pairs:
            assert split_team(left) != split_team(right), (left, right)

    def test_international_qualifier_forms_join(self):
        # Given Libertadores spellings with different qualifier syntaxes
        pairs = [("Nacional (URU)", "Nacional-URU"), ("Guaraní (PAR)", "Guaraní-PAR")]
        # When normalized
        # Then parenthesised and hyphenated forms are the same club
        for left, right in pairs:
            assert split_team(left) == split_team(right), (left, right)

    def test_brazilian_and_paraguayan_guarani_stay_distinct(self):
        assert split_team("Guarani") == ("guarani", "sp")
        assert split_team("Guaraní-PAR") == ("guarani", "par")
        assert split_team("Guarani") != split_team("Guaraní-PAR")

    def test_parenthetical_notes_are_dropped(self):
        # Given the Copa do Brasil's longest team name
        raw = "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"
        # When normalized
        base, qualifier = split_team(raw)
        # Then the historical note is gone and the state is kept
        assert base == "boavista sport club"
        assert qualifier == "rj"

    def test_fifa_club_with_state_in_parentheses(self):
        assert split_team("América FC (Minas Gerais)") == ("america", "mg")


class TestDateParsing:
    def test_iso_datetime_with_time(self):
        parsed, time = parse_date("2012-05-19 18:30:00")
        assert parsed == date(2012, 5, 19)
        assert time == "18:30"

    def test_brazilian_day_first_format(self):
        parsed, time = parse_date("29/03/2003")
        assert parsed == date(2003, 3, 29)
        assert time is None

    def test_plain_iso_date(self):
        parsed, time = parse_date("2023-09-24")
        assert parsed == date(2023, 9, 24)
        assert time is None

    def test_missing_values(self):
        for bad in ("", "NA", "-", None):
            assert parse_date(bad) == (None, None)


class TestNumberParsing:
    def test_float_strings_become_ints(self):
        assert parse_int("1.0") == 1
        assert parse_int("2") == 2
        assert parse_int(3.0) == 3

    def test_missing_values(self):
        for bad in ("", "NA", "-", None, "x"):
            assert parse_int(bad) is None


class TestUtf8TeamResolution:
    def test_accented_names_resolve_through_the_repository(self, repo):
        # Given accented club names typed by a user
        # When resolved against the loaded repository
        # Then each resolves to exactly one team entity
        for query, expected_key in [
            ("Grêmio", "gremio"),
            ("Avaí", "avai"),
            ("Fortaleza", "fortaleza"),
            ("Atlético-MG", "atletico mg"),
            ("São Paulo", "sao paulo"),
        ]:
            entities = repo.resolve_team(query)
            keys = [entity.key for entity in entities]
            assert expected_key in keys, (query, keys)
