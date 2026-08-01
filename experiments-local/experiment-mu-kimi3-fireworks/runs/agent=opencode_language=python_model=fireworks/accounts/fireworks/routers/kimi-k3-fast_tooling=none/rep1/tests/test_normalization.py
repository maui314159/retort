"""Unit tests for team-name, text and date normalization."""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp.normalization import (
    TeamRegistry,
    normalize_text,
    parse_date,
    parse_team,
    strip_accents,
    team_base,
    team_key,
)


class TestStripAccents:
    def test_accents_removed(self):
        assert strip_accents("São Paulo") == "Sao Paulo"
        assert strip_accents("Grêmio") == "Gremio"
        assert strip_accents("Avaí") == "Avai"

    def test_cedilla(self):
        assert strip_accents("Confiança") == "Confianca"

    def test_empty(self):
        assert strip_accents("") == ""


class TestNormalizeText:
    def test_case_and_whitespace(self):
        assert normalize_text("  Flamengo ") == "flamengo"

    def test_punctuation_collapsed(self):
        assert normalize_text("A.b.c.") == "a b c"


class TestParseTeam:
    @pytest.mark.parametrize(
        "raw,expected_base",
        [
            ("Palmeiras-SP", "palmeiras"),
            ("Palmeiras", "palmeiras"),
            ("palmeiras", "palmeiras"),
            ("Sport Club Corinthians Paulista", "corinthians"),
            ("Corinthians-SP", "corinthians"),
            ("São Paulo", "sao paulo"),
            ("Sao Paulo", "sao paulo"),
            ("Grêmio", "gremio"),
            ("Flamengo-RJ", "flamengo"),
            ("Vasco", "vasco"),
            ("Vasco da Gama-RJ", "vasco"),
            ("Vasco Da Gama RJ", "vasco"),
            ("Athletico-PR", "atletico"),
            ("Atletico-PR", "atletico"),
            ("Atletico Paranaense", "atletico"),
            ("Atlético-MG", "atletico"),
            ("Atletico Mineiro", "atletico"),
            ("Sport", "sport"),
            ("Sport-PE", "sport"),
            ("Sport Recife", "sport"),
            ("Sport Club do Recife", "sport"),
            ("Fortaleza", "fortaleza"),
            ("Fortaleza FC", "fortaleza"),
            ("Fortaleza-CE", "fortaleza"),
            ("Ceará Sporting Club", "ceara"),
            ("Santa Cruz FC", "santa cruz"),
            ("Joinville", "joinville"),
            ("Red Bull Bragantino-SP", "bragantino"),
            ("Botafogo RJ", "botafogo"),
            ("Boca Juniors", "boca juniors"),
        ],
    )
    def test_base(self, raw, expected_base):
        assert parse_team(raw)[0] == expected_base

    @pytest.mark.parametrize(
        "raw,expected_state",
        [
            ("Palmeiras-SP", "sp"),
            ("Palmeiras", "sp"),  # via alias
            ("Flamengo-RJ", "rj"),
            ("América - MG", "mg"),
            ("América-MG", "mg"),
            ("América-RN", "rn"),
            ("America MG", "mg"),
            ("Nacional (URU)", "uru"),
            ("Barcelona-EQU", "equ"),
            ("Boca Juniors", None),
        ],
    )
    def test_state(self, raw, expected_state):
        assert parse_team(raw)[1] == expected_state

    def test_america_states_are_distinct(self):
        assert team_key("América-MG") != team_key("América-RN")

    def test_state_suffix_equivalence(self):
        assert team_key("Palmeiras-SP") == team_key("Palmeiras")
        assert team_key("Flamengo-RJ") == team_key("Flamengo")

    def test_none_and_nan(self):
        assert parse_team(None) == ("", None)
        assert team_key(None) == ""

    def test_club_suffix_stripped(self):
        assert team_base("4 de Julho EC") == "4 de julho"


class TestTeamRegistry:
    def test_resolve_exact_and_fuzzy(self):
        reg = TeamRegistry()
        reg.register("Flamengo-RJ")
        reg.register("Flamengo")
        assert reg.resolve("Flamengo") == ["flamengo rj"]
        assert reg.resolve("flamengo") == ["flamengo rj"]
        assert reg.resolve("FLAMENGO") == ["flamengo rj"]

    def test_resolve_ambiguous_base(self):
        reg = TeamRegistry()
        reg.register("América-MG")
        reg.register("América-RN")
        assert sorted(reg.resolve("América")) == ["america mg", "america rn"]

    def test_resolve_unknown(self):
        reg = TeamRegistry()
        assert reg.resolve("Real Madrid") == []

    def test_display_prefers_shortest(self):
        reg = TeamRegistry()
        reg.register("Flamengo-RJ")
        reg.register("Flamengo")
        assert reg.display_name("flamengo rj") == "Flamengo"

    def test_display_fallback(self):
        reg = TeamRegistry()
        assert reg.display_name("boca juniors") == "Boca Juniors"


class TestParseDate:
    @pytest.mark.parametrize(
        "text,year,month,day",
        [
            ("2023-09-24", 2023, 9, 24),
            ("2012-05-19 18:30:00", 2012, 5, 19),
            ("29/03/2003", 2003, 3, 29),
            ("2023-09-24 20:00", 2023, 9, 24),
        ],
    )
    def test_formats(self, text, year, month, day):
        dt = parse_date(text)
        assert (dt.year, dt.month, dt.day) == (year, month, day)

    def test_time_component_parsed(self):
        dt = parse_date("2012-05-19 18:30:00")
        assert (dt.hour, dt.minute) == (18, 30)

    def test_invalid_returns_none(self):
        assert parse_date("not a date") is None
        assert parse_date("") is None
        assert parse_date(None) is None
