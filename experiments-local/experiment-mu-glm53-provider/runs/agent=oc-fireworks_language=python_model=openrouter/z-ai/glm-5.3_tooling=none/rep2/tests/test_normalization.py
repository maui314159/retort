"""BDD scenarios for team-name and date normalization.

Feature: Team name normalization
  The datasets spell one club in many ways ("Palmeiras-SP", "Palmeiras - SP",
  "Palmeiras", "Atletico Mineiro"). Every spelling must fold to the same
  canonical identity, ambiguous names must be disambiguated, and the three
  dataset date formats must all parse.
"""

from __future__ import annotations

from datetime import date

from brazilian_soccer.normalize import fold, parse_date, parse_name, to_int


class TestFolding:
    def test_accents_case_and_punctuation_are_ignored(self):
        # Given differently spelled versions of the same name
        # When they are folded
        # Then they all produce the same key
        assert fold("São Paulo") == fold("SAO PAULO") == fold("sao-paulo")
        assert fold("Grêmio") == fold("Gremio")
        assert fold("América - MG") == fold("america mg")

    def test_athletico_atletico_spelling_variants_unify(self):
        # Given the post-2019 "Athletico" spelling change
        # When both spellings are folded
        # Then they are equal
        assert fold("Athletico-PR") == fold("Atlético-PR")


class TestNameParsing:
    def test_state_suffixes_are_detected_in_all_formats(self):
        # Given names with state suffixes in different styles
        # When parsed
        # Then the state is extracted in every case
        for raw in ("Palmeiras-SP", "América - MG", "Botafogo RJ"):
            parsed = parse_name(raw)
            assert parsed.state is not None, raw
            assert parsed.country is None

    def test_decorative_club_tokens_are_stripped(self):
        # Given names carrying FC/EC decorations
        # When parsed
        # Then the base excludes the decoration
        assert parse_name("Fortaleza FC").base == parse_name("Fortaleza").base
        assert parse_name("EC Bahia").base == parse_name("Bahia").base

    def test_parenthetical_country_tags_are_detected(self):
        # Given Libertadores names like "Nacional (URU)"
        # When parsed
        # Then the country is extracted and kept for identity
        parsed = parse_name("Nacional (URU)")
        assert parsed.country == "URU"
        assert parsed.state is None

    def test_antigo_parenthetical_junk_is_removed(self):
        # Given the cup file's verbose historical names
        # When parsed
        # Then the "(antigo ...)" note is dropped
        parsed = parse_name(
            "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"
        )
        assert "antigo" not in fold(parsed.pretty)
        assert parsed.state == "RJ"


class TestRegistryResolution:
    def test_full_historical_names_resolve_via_aliases(self, dataset):
        # Given full official club names
        # When resolved
        # Then they map to the same entity as the short dataset spellings
        cases = {
            "Atletico Mineiro": "atleticomg",
            "Atlético Paranaense": "atleticopr",
            "Sport Club do Recife": "sportpe",
            "Ceará Sporting Club": "cearace",
            "Vasco": "vascodagamarj",
            "Red Bull Bragantino": "redbullbragantinosp",
        }
        for query, expected in cases.items():
            resolution = dataset.registry.resolve(query)
            assert resolution.matched, query
            assert resolution.key == expected, query

    def test_bare_dominant_base_resolves_to_major_club(self, dataset):
        # Given a bare name shared by a giant and a tiny club
        # When resolved
        # Then the dominant club wins
        resolution = dataset.registry.resolve("Flamengo")
        assert resolution.matched
        assert resolution.key == "flamengorj"

    def test_rare_state_variants_still_resolve(self, dataset):
        # Given the explicitly suffixed small club
        # When resolved
        # Then it maps to its own entity, not the giant
        resolution = dataset.registry.resolve("Flamengo-PI")
        assert resolution.matched
        assert resolution.key == "flamengopi"

    def test_genuinely_ambiguous_base_returns_candidates(self, dataset):
        # Given a base shared by several clubs with no dominant one
        # When resolved
        # Then a disambiguation list is returned
        resolution = dataset.registry.resolve("atletico")
        assert not resolution.matched
        assert len(resolution.ambiguous) >= 3
        displays = " / ".join(t.display for t in resolution.ambiguous)
        assert "Atlético-MG" in displays
        assert "Atlético-PR" in displays

    def test_unknown_name_returns_close_suggestions(self, dataset):
        # Given a misspelled name
        # When resolved
        # Then close matches are suggested
        resolution = dataset.registry.resolve("Flmenego")
        assert not resolution.matched
        assert any("Flamengo" in name for name in resolution.suggestions)

    def test_split_entities_are_merged(self, dataset):
        # Given all sources are loaded
        # When displays are compared
        # Then no two distinct keys share one display name
        by_display: dict[str, set[str]] = {}
        for key, team in dataset.registry.teams.items():
            by_display.setdefault(team.display, set()).add(key)
        splits = {d: ks for d, ks in by_display.items() if len(ks) > 1}
        assert not splits


class TestDateParsing:
    def test_all_dataset_date_formats_parse(self):
        # Given the three date formats used across the files
        # When parsed
        # Then each yields the correct date
        assert parse_date("2012-05-19 18:30:00") == date(2012, 5, 19)
        assert parse_date("2023-09-24") == date(2023, 9, 24)
        assert parse_date("29/03/2003") == date(2003, 3, 29)

    def test_missing_values_return_none(self):
        # Given NA / empty / dash placeholders
        # When parsed
        # Then None comes back instead of an error
        for bad in ("NA", "-", "", None):
            assert parse_date(bad) is None

    def test_to_int_handles_float_strings_and_placeholders(self):
        # Given the extended file's "2.0" style numbers
        # When converted
        # Then integers come back, placeholders become None
        assert to_int("2.0") == 2
        assert to_int("NA") is None
        assert to_int("-") is None
