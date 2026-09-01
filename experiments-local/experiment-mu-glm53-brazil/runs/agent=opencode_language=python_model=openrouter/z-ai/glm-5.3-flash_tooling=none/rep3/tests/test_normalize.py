"""Unit tests for the normalization layer."""

from __future__ import annotations

from datetime import date

import pytest

from brazilian_soccer.normalize import (
    TeamRegistry,
    canonical_key,
    parse_date,
    parse_int,
    parse_team_name,
    strip_accents,
)


class TestCanonicalKey:
    @pytest.mark.parametrize("raw,expected", [
        ("São Paulo", "saopaulo"),
        ("Sao Paulo", "saopaulo"),
        ("A.b.c.", "abc"),
        ("EC Bahia", "bahia"),
        ("Vitoria F. C.", "vitoria"),
    ])
    def test_keys(self, raw, expected):
        assert canonical_key(raw) == expected

    def test_key_of_parsed_base(self):
        # In the real pipeline the state/country suffix is parsed out first.
        base, code = parse_team_name("ABC - RN")
        assert (canonical_key(base), code) == ("abc", "RN")
        base, code = parse_team_name("Nacional (URU)")
        assert (canonical_key(base), code) == ("nacional", "URU")

    def test_strip_accents(self):
        assert strip_accents("Grêmio") == "Gremio"
        assert strip_accents("Avaí") == "Avai"


class TestParseTeamName:
    @pytest.mark.parametrize("raw,base,code", [
        ("Palmeiras-SP", "Palmeiras", "SP"),
        ("Atlético - MG", "Atlético", "MG"),
        ("America MG", "America", "MG"),
        ("River (PI)", "River", "PI"),
        ("Nacional (URU)", "Nacional", "URU"),
        ("Barcelona-EQU", "Barcelona", "EQU"),
        ("ASA AL", "ASA", "AL"),
        ("Cuiaba MT", "Cuiaba", "MT"),
        ("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ",
         "Boavista Sport Club", "RJ"),
        ("Rentistas", "Rentistas", None),
        ("Corinthians", "Corinthians", None),
    ])
    def test_parsing(self, raw, base, code):
        assert parse_team_name(raw) == (base, code)


class TestParseDate:
    @pytest.mark.parametrize("raw,expected", [
        ("2023-09-24", date(2023, 9, 24)),
        ("2012-05-19 18:30:00", date(2012, 5, 19)),
        ("29/03/2003", date(2003, 3, 29)),
        ("", None),
        (None, None),
        ("NA", None),
    ])
    def test_formats(self, raw, expected):
        assert parse_date(raw) == expected

    def test_parse_int(self):
        assert parse_int("2") == 2
        assert parse_int("2.0") == 2
        assert parse_int("") is None
        assert parse_int("-") is None
        assert parse_int(None) is None


class TestTeamRegistry:
    def _registry(self, *raws: str) -> TeamRegistry:
        reg = TeamRegistry()
        for raw in raws:
            reg.register(raw)
        reg.finalize()
        return reg

    def test_state_suffix_variants_merge(self):
        reg = self._registry("Palmeiras-SP", "Palmeiras - SP", "Palmeiras")
        assert reg.key_for("Palmeiras-SP") == reg.key_for("Palmeiras")

    def test_accents_merge(self):
        reg = self._registry("Sao Paulo-SP", "São Paulo", "Sao Paulo")
        assert reg.key_for("São Paulo") == reg.key_for("Sao Paulo-SP")

    def test_ambiguous_base_uses_state(self):
        reg = self._registry("Botafogo-RJ", "Botafogo - PB", "Botafogo SP")
        assert reg.key_for("Botafogo-RJ") != reg.key_for("Botafogo - PB")
        assert reg.key_for("Botafogo-RJ") != reg.key_for("Botafogo SP")

    def test_bare_name_defaults_to_famous_club(self):
        reg = self._registry("Botafogo-RJ", "Botafogo - PB", "Botafogo")
        assert reg.key_for("Botafogo") == reg.key_for("Botafogo-RJ")

    def test_country_code_is_identity(self):
        reg = self._registry("Nacional (URU)", "Nacional-URU", "Nacional - AM")
        assert reg.key_for("Nacional (URU)") != reg.key_for("Nacional - AM")
        assert reg.key_for("Nacional-URU") == reg.key_for("Nacional (URU)")

    def test_unambiguous_state_is_dropped(self):
        reg = self._registry("Cuiaba MT", "Cuiabá - MT", "Cuiaba")
        assert reg.key_for("Cuiaba MT") == reg.key_for("Cuiaba")

    def test_alias_full_name(self):
        reg = self._registry("Atlético-MG", "Atletico Mineiro", "Atlético - MG")
        assert reg.key_for("Atletico Mineiro") == reg.key_for("Atlético-MG")

    def test_display_names_readable(self):
        reg = self._registry("Flamengo-RJ", "Flamengo", "Gremio", "Grêmio - RS")
        assert reg.display(reg.key_for("Flamengo-RJ")).startswith("Flamengo")
        assert reg.display(reg.key_for("Gremio")) in ("Grêmio", "Gremio")

    def test_register_after_finalize(self):
        reg = self._registry("Flamengo-RJ", "Flamengo - PI")
        assert reg.key_for("Flamengo") == reg.key_for("Flamengo-RJ")
