"""GWT unit tests for text, date and team-name normalization."""

from __future__ import annotations

from datetime import date

from soccer_mcp.clubs import resolve_club
from soccer_mcp.normalize import (
    normalize_text,
    parse_datetime,
    parse_int,
    parse_money_eur,
    split_state_suffix,
    strip_accents,
)


class TestNormalizeText:
    """Scenario: normalization handles Brazilian Portuguese text."""

    def test_given_accented_team_names_when_normalized_then_ascii_keys(self):
        # Given accented names from the datasets
        # When normalized
        # Then accents are stripped and keys are lowercase
        assert strip_accents("São Paulo") == "Sao Paulo"
        assert strip_accents("Grêmio") == "Gremio"
        assert strip_accents("Avaí") == "Avai"
        assert strip_accents("Fortaleza Esporte Clube") == "Fortaleza Esporte Clube"
        assert normalize_text("Grêmio - RS") == "gremio rs"
        assert normalize_text("América FC (Minas Gerais)") == "america fc minas gerais"
        assert normalize_text("A.s.a. - AL") == "asa al"
        assert normalize_text("Botafogo-RJ") == "botafogo rj"

    def test_given_extra_whitespace_and_case_when_normalized_then_collapsed(self):
        assert normalize_text("  Vasco   da  Gama ") == "vasco da gama"
        assert normalize_text("CORINTHIANS") == "corinthians"


class TestDateParsing:
    """Scenario: multiple date formats parse to dates."""

    def test_given_iso_datetime_when_parsed_then_date_and_time(self):
        d, t = parse_datetime("2012-05-19 18:30:00")
        assert d == date(2012, 5, 19)
        assert t == "18:30"

    def test_given_iso_date_when_parsed_then_date(self):
        assert parse_datetime("2023-09-24") == (date(2023, 9, 24), None)

    def test_given_brazilian_date_when_parsed_then_date(self):
        assert parse_datetime("29/03/2003") == (date(2003, 3, 29), None)

    def test_given_empty_or_invalid_when_parsed_then_none(self):
        assert parse_datetime("") == (None, None)
        assert parse_datetime("NA") == (None, None)
        assert parse_datetime(None) == (None, None)


class TestLooseIntParsing:
    def test_given_na_and_float_strings_when_parsed_then_int_or_none(self):
        assert parse_int("NA") is None
        assert parse_int("") is None
        assert parse_int("2.0") == 2
        assert parse_int("12") == 12
        assert parse_int(None) is None


class TestMoneyParsing:
    def test_given_fifa_value_strings_when_parsed_then_eur(self):
        assert parse_money_eur("€110.5M") == 110_500_000
        assert parse_money_eur("€565K") == 565_000
        assert parse_money_eur("") is None


class TestStateSuffix:
    def test_given_brazilian_ufs_when_split_then_state_returned(self):
        assert split_state_suffix("atletico pr") == ("atletico", "PR")
        assert split_state_suffix("flamengo rj") == ("flamengo", "RJ")

    def test_given_foreign_codes_when_split_then_kept_in_base(self):
        # URU/PAR/EQU are not Brazilian UFs: they must not be stripped
        assert split_state_suffix("nacional uru") == ("nacional uru", None)
        assert split_state_suffix("barcelona equ") == ("barcelona equ", None)


class TestClubResolution:
    """Scenario: team name variations resolve to the same club."""

    def test_given_state_suffixed_variants_when_resolved_then_same_club(self):
        cases = [
            ("Palmeiras-SP", "palmeiras"),
            ("Palmeiras - SP", "palmeiras"),
            ("Palmeiras", "palmeiras"),
            ("SE Palmeiras", "palmeiras"),
            ("Flamengo-RJ", "flamengo"),
            ("CR Flamengo", "flamengo"),
            ("Grêmio-RS", "gremio"),
            ("Gremio", "gremio"),
            ("Atlético Mineiro", "atletico_mg"),
            ("Atletico-MG", "atletico_mg"),
            ("Atlético - MG", "atletico_mg"),
            ("Athletico Paranaense - PR", "atletico_pr"),
            ("Atletico-PR", "atletico_pr"),
            ("Atletico Paranaense", "atletico_pr"),
            ("Athletico", "atletico_pr"),  # bare form used by Libertadores file
            ("Sport Club do Recife", "sport"),
            ("Sport-PE", "sport"),
            ("Sport Recife", "sport"),
            ("América FC (Minas Gerais)", "america_mg"),
            ("America-MG", "america_mg"),
            ("Vasco da Gama-RJ", "vasco"),
            ("Vasco", "vasco"),
            ("Ceará Sporting Club", "ceara"),
            ("Ceara-CE", "ceara"),
            ("Red Bull Bragantino-SP", "bragantino"),
            ("Bragantino", "bragantino"),
        ]
        for raw, expected_id in cases:
            club = resolve_club(raw)
            assert club is not None, f"could not resolve {raw!r}"
            assert club.club_id == expected_id, f"{raw!r} -> {club.club_id}"

    def test_given_same_name_different_states_when_resolved_then_distinct(self):
        # Flamengo-PI is a different club from Flamengo-RJ
        major = resolve_club("Flamengo")
        minor = resolve_club("Flamengo-PI")
        assert major.club_id == "flamengo"
        assert minor is None or minor.club_id == "flamengo_pi"
        assert (minor is None) or minor.club_id != major.club_id

        assert resolve_club("Botafogo-PB").club_id == "botafogo_pb"
        assert resolve_club("Botafogo-SP").club_id == "botafogo_sp"
        assert resolve_club("Santa Cruz-RN").club_id == "santa_cruz_rn"

    def test_given_foreign_libertadores_names_when_resolved_then_not_brazilian(self):
        # Foreign clubs fall outside the curated registry
        assert resolve_club("Boca Juniors") is None
        assert resolve_club("River Plate") is None
        assert resolve_club("Nacional (URU)") is None
