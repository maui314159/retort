"""Unit tests for team-name parsing, canonicalization and value parsing."""

from __future__ import annotations

from datetime import date

from brazilian_soccer_mcp.normalize import (
    TeamRegistry,
    base_norm,
    parse_date,
    parse_int,
    parse_team_name,
    strip_accents,
)


class TestStripAccents:
    def test_accents_folded(self):
        assert strip_accents("São Paulo Grêmio Avaí") == "Sao Paulo Gremio Avai"

    def test_cedilla(self):
        assert strip_accents("Fortaleza") == "Fortaleza"


class TestBaseNorm:
    def test_punctuation_removed(self):
        assert base_norm("Red Bull Bragantino-SP") == "red bull bragantino sp"

    def test_parenthetical_removed(self):
        assert base_norm("Nacional (URU)") == "nacional"


class TestParseTeamName:
    def test_state_suffix_extracted(self):
        parsed = parse_team_name("Palmeiras-SP")
        assert parsed.bare == "palmeiras"
        assert parsed.uf == "SP"

    def test_space_state_suffix(self):
        parsed = parse_team_name("América - MG")
        assert parsed.bare == "america"
        assert parsed.uf == "MG"

    def test_no_suffix(self):
        parsed = parse_team_name("Flamengo")
        assert parsed.bare == "flamengo"
        assert parsed.uf is None

    def test_state_hint_used(self):
        parsed = parse_team_name("São Paulo", uf_hint="SP")
        assert parsed.bare == "sao paulo"
        assert parsed.uf == "SP"

    def test_noise_tokens_removed(self):
        parsed = parse_team_name("Sport Club do Recife")
        assert parsed.bare == "sport do recife"

    def test_sport_is_not_noise(self):
        parsed = parse_team_name("Sport-PE")
        assert parsed.bare == "sport"
        assert parsed.uf == "PE"

    def test_country_code_extracted(self):
        parsed = parse_team_name("Nacional-URU")
        assert parsed.bare == "nacional"
        assert parsed.country == "URU"

    def test_country_code_in_parentheses(self):
        parsed = parse_team_name("Nacional (URU)")
        assert parsed.bare == "nacional"
        assert parsed.country == "URU"

    def test_state_name_in_parentheses(self):
        parsed = parse_team_name("América FC (Minas Gerais)")
        assert parsed.bare == "america"
        assert parsed.uf == "MG"

    def test_full_official_name(self):
        parsed = parse_team_name("Sport Club Corinthians Paulista")
        assert parsed.bare == "sport corinthians paulista"


class TestTeamRegistry:
    def _registry(self) -> TeamRegistry:
        registry = TeamRegistry()
        for _ in range(10):
            registry.observe("Flamengo-RJ", "RJ")
            registry.observe("Fluminense-RJ", "RJ")
        registry.observe("Flamengo")
        registry.observe("Flamengo-PI", "PI")
        for _ in range(5):
            registry.observe("Atletico-MG", "MG")
            registry.observe("Atletico-GO", "GO")
        for _ in range(4):
            registry.observe("Palmeiras-SP", "SP")
        registry.observe("Nacional-URU")
        registry.observe("Nacional (PAR)")
        registry.finalize()
        return registry

    def test_unambiguous_bare_keeps_short_key(self):
        registry = self._registry()
        assert registry.canonical("Palmeiras") == "palmeiras"
        assert registry.canonical("Palmeiras-SP") == "palmeiras"

    def test_ambiguous_bare_splits_by_state(self):
        registry = self._registry()
        assert registry.canonical("Atletico-MG") == "atletico-mg"
        assert registry.canonical("Atletico-GO") == "atletico-go"

    def test_suffixless_mentions_merge_into_major_state(self):
        registry = self._registry()
        assert registry.canonical("Flamengo") == "flamengo-rj"
        assert registry.canonical("Flamengo-RJ") == "flamengo-rj"

    def test_country_codes_stay_distinct(self):
        registry = self._registry()
        assert registry.canonical("Nacional-URU") == "nacional-uru"
        assert registry.canonical("Nacional (PAR)") == "nacional-par"

    def test_display_prefers_plain_name(self):
        registry = self._registry()
        assert registry.display("flamengo-rj") == "Flamengo"

    def test_resolve_exact(self):
        registry = self._registry()
        resolution = registry.resolve("Palmeiras-SP")
        assert resolution.found
        assert resolution.key == "palmeiras"
        assert resolution.matched_by == "exact"

    def test_resolve_frequency_prefers_major_club(self):
        registry = self._registry()
        resolution = registry.resolve("Flamengo")
        assert resolution.key == "flamengo-rj"
        assert resolution.matched_by == "frequency"
        assert any(alt["key"] == "flamengo-pi"
                   for alt in resolution.alternatives)

    def test_resolve_full_official_name_by_token_subset(self):
        registry = self._registry()
        registry.observe("Corinthians-SP", "SP")
        registry.finalize()
        resolution = registry.resolve("Sport Club Corinthians Paulista")
        assert resolution.found
        assert resolution.key == "corinthians"

    def test_resolve_unknown_reports_not_found(self):
        registry = self._registry()
        resolution = registry.resolve("Galactic United")
        assert not resolution.found

    def test_alias_applied(self):
        registry = self._registry()
        registry.observe("Vasco da Gama-RJ", "RJ")
        registry.observe("Atletico Paranaense", "PR")
        registry.finalize()
        assert registry.canonical("Vasco") == "vasco da gama"
        assert registry.canonical("Athletico") == "atletico-pr"


class TestParseDate:
    def test_iso_with_time(self):
        assert parse_date("2012-05-19 18:30:00") == date(2012, 5, 19)

    def test_iso_date_only(self):
        assert parse_date("2023-09-24") == date(2023, 9, 24)

    def test_brazilian_format(self):
        assert parse_date("29/03/2003") == date(2003, 3, 29)

    def test_brazilian_format_with_time(self):
        assert parse_date("29/03/2003 16:00") == date(2003, 3, 29)

    def test_na_and_dash(self):
        assert parse_date("NA") is None
        assert parse_date("-") is None
        assert parse_date("") is None
        assert parse_date(None) is None


class TestParseInt:
    def test_plain_and_float_forms(self):
        assert parse_int("2") == 2
        assert parse_int("1.0") == 1
        assert parse_int(3) == 3

    def test_invalid_markers(self):
        assert parse_int("-") is None
        assert parse_int("") is None
        assert parse_int("NA") is None
        assert parse_int(None) is None
