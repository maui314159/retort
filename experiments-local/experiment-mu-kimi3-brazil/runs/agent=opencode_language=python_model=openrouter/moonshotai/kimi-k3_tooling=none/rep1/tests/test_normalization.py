"""Unit tests for name/date normalization."""

from __future__ import annotations

from datetime import date, datetime

from brazilian_soccer_mcp.normalization import (
    clean_team_name,
    parse_date,
    strip_accents,
    team_key,
)


class TestStripAccents:
    def test_removes_accents(self):
        assert strip_accents("São Paulo") == "Sao Paulo"
        assert strip_accents("Grêmio") == "Gremio"
        assert strip_accents("Avaí") == "Avai"

    def test_keeps_ascii(self):
        assert strip_accents("Fortaleza") == "Fortaleza"


class TestCleanTeamName:
    def test_normalizes_dash_suffix_to_space(self):
        assert clean_team_name("Palmeiras-SP") == "Palmeiras SP"
        assert clean_team_name("América - MG") == "América MG"

    def test_removes_parenthetical_notes(self):
        raw = "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"
        assert clean_team_name(raw) == "Boavista Sport Club RJ"

    def test_keeps_country_code_parenthetical(self):
        # Country codes disambiguate clubs and must survive cleaning.
        assert clean_team_name("Nacional (URU)") == "Nacional URU"

    def test_preserves_utf8(self):
        assert clean_team_name("Grêmio-RS") == "Grêmio RS"


class TestTeamKey:
    def test_state_suffix_variants_match(self):
        assert team_key("Palmeiras-SP") == team_key("Palmeiras") == "palmeiras"
        assert team_key("Flamengo-RJ") == team_key("Flamengo") == "flamengo"

    def test_accents_are_ignored_for_matching(self):
        assert team_key("Grêmio") == team_key("Gremio RS") == "gremio"
        assert team_key("São Paulo") == team_key("Sao Paulo-SP") == "saopaulo"

    def test_atletico_paranaense_rename_aliases(self):
        # Club renamed Atlético -> Athletico Paranaense in 2019.
        assert team_key("Atletico-PR") == "athleticoparanaense"
        assert team_key("Athletico") == "athleticoparanaense"
        assert team_key("Atlético Paranaense") == "athleticoparanaense"

    def test_same_base_name_different_states_stay_distinct(self):
        assert team_key("Botafogo SP") != team_key("Botafogo RJ")
        assert team_key("Botafogo-PB") != team_key("Botafogo")
        assert team_key("Fluminense PI") != team_key("Fluminense")
        assert team_key("Santos AP") != team_key("Santos")

    def test_unknown_suffixed_atletico_stays_distinct(self):
        assert team_key("Atletico - ES") != team_key("Atletico-PR")
        assert team_key("Atlético - BA") != "athleticoparanaense"

    def test_america_variants(self):
        assert team_key("América - MG") == team_key("America MG") == "americamineiro"
        assert team_key("America RN") == "americanatal"
        assert team_key("America RN") != team_key("America MG")

    def test_ec_prefix_variants(self):
        assert team_key("EC Bahia") == team_key("Bahia") == "bahia"
        assert team_key("EC Vitoria") == team_key("Vitória-BA") == "vitoria"

    def test_country_parentheticals_stay_distinct(self):
        assert team_key("Nacional (URU)") != team_key("Nacional (PAR)")

    def test_empty_name(self):
        assert team_key("") == ""
        assert team_key(None) == ""


class TestParseDate:
    def test_iso_with_time(self):
        assert parse_date("2012-05-19 18:30:00") == date(2012, 5, 19)

    def test_iso_date(self):
        assert parse_date("2023-09-24") == date(2023, 9, 24)

    def test_brazilian_format(self):
        assert parse_date("29/03/2003") == date(2003, 3, 29)

    def test_passthrough(self):
        assert parse_date(date(2020, 1, 1)) == date(2020, 1, 1)
        assert parse_date(datetime(2020, 1, 1, 12, 0)) == date(2020, 1, 1)

    def test_invalid(self):
        assert parse_date("not a date") is None
        assert parse_date("") is None
        assert parse_date(None) is None
