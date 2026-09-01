"""BDD tests for team-name normalization.

Feature: Team name normalization
  The datasets spell one club in many ways; the registry must fold all
  spellings into one entity so statistics join correctly across files.
"""

from __future__ import annotations

import pytest

from soccer_mcp.normalize import (
    TeamRegistry,
    collapse,
    parse_team_name,
    strip_accents,
)

# ----------------------------------------------------------------------
# Unit: text helpers
# ----------------------------------------------------------------------


class TestTextHelpers:
    """Scenario: Unicode folding
    Given Brazilian Portuguese team names with accents
    Then accents are stripped for matching
    """

    def test_strip_accents(self):
        assert strip_accents("Grêmio") == "Gremio"
        assert strip_accents("São Paulo") == "Sao Paulo"
        assert strip_accents("Criciúma") == "Criciuma"

    def test_collapse(self):
        assert collapse("São Paulo") == "sao paulo"
        assert collapse("América FC (Minas Gerais)") == "america fc minas gerais"
        assert collapse("A.s.a. - AL") == "a s a al"
        assert collapse("Red Bull Bragantino-SP") == "red bull bragantino sp"

    def test_collapse_dots(self):
        """Dotted abbreviations equal their plain form: A.s.a. == ASA."""
        assert collapse("A.b.c.") == "abc"
        assert collapse("ABC") == "abc"


# ----------------------------------------------------------------------
# Unit: suffix parsing
# ----------------------------------------------------------------------


class TestParseTeamName:
    """Scenario: State suffix parsing
    Given names like "Palmeiras-SP", "América - MG" and "Botafogo SP"
    Then the state code is separated from the club base name
    """

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("Palmeiras-SP", ("palmeiras", "SP")),
            ("América - MG", ("america", "MG")),
            ("Botafogo SP", ("botafogo", "SP")),
            ("Fluminense-RJ", ("fluminense", "RJ")),
            ("4 de Julho - PI", ("4 de julho", "PI")),
            ("Cuiaba MT", ("cuiaba", "MT")),
            ("Coritiba PR", ("coritiba", "PR")),
        ],
    )
    def test_state_suffix(self, raw, expected):
        assert parse_team_name(raw) == expected

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("Nacional (URU)", ("nacional", "URU")),
            ("Guaraní-PAR", ("guarani", "PAR")),
            ("Barcelona-EQU", ("barcelona", "EQU")),
        ],
    )
    def test_country_suffix(self, raw, expected):
        assert parse_team_name(raw) == expected

    def test_no_suffix(self):
        assert parse_team_name("Boca Juniors") == ("boca juniors", None)

    def test_suffix_not_a_state(self):
        """'EC'/'FC' endings are part of the club name, not a state."""
        base, region = parse_team_name("Fortaleza EC")
        assert region is None
        assert base == "fortaleza ec"


# ----------------------------------------------------------------------
# Unit: full-name aliases
# ----------------------------------------------------------------------


class TestAliases:
    """Scenario: Full club names and era renames
    Given "Atletico Mineiro" (FIFA) and "Atlético-MG" (match files)
    Then both resolve to the same entity
    """

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("Atletico Mineiro", ("atletico", "MG")),
            ("Atlético Mineiro", ("atletico", "MG")),
            ("Atlético-MG", ("atletico", "MG")),
            ("Atletico Paranaense", ("atletico", "PR")),
            ("Athletico Paranaense", ("atletico", "PR")),
            ("Vasco da Gama", ("vasco", "RJ")),
            ("Vasco da Gama - RJ", ("vasco", "RJ")),
            ("Vasco Da Gama RJ", ("vasco", "RJ")),
            ("Red Bull Bragantino", ("bragantino", "SP")),
            ("Sport Club do Recife", ("sport", "PE")),
            ("América FC (Minas Gerais)", ("america", "MG")),
            ("Ceará Sporting Club", ("ceara", "CE")),
            ("EC Juventude", ("juventude", "RS")),
        ],
    )
    def test_alias_key(self, raw, expected):
        from soccer_mcp.normalize import canonical_key

        assert canonical_key(raw) == expected


# ----------------------------------------------------------------------
# Integration: registry resolution over the real datasets
# ----------------------------------------------------------------------


class TestRegistryResolution:
    """Scenario: Resolve user queries against the loaded registry
    Given a user typing any common spelling of a club
    Then the registry returns the right entity first
    """

    def test_exact_spellings(self, registry):
        for query, display in [
            ("Palmeiras", "Palmeiras"),
            ("palmeiras-sp", "Palmeiras"),
            ("São Paulo", "São Paulo"),
            ("sao paulo", "São Paulo"),
            ("Grêmio", "Grêmio"),
            ("gremio", "Grêmio"),
            ("Athletico-PR", "Athletico-PR"),
            ("Atletico Mineiro", "Atlético-MG"),
            ("Vasco", "Vasco da Gama"),
            ("Red Bull Bragantino", "Red Bull Bragantino"),
            ("Sport Club do Recife", "Sport"),
        ]:
            teams = registry.resolve(query)
            assert teams, f"no resolution for {query!r}"
            assert teams[0].display == display, f"{query!r} -> {teams[0].display}"

    def test_disambiguation_by_prominence(self, registry):
        """Plain 'Botafogo' means the famous RJ club, but PB/SP exist too."""
        teams = registry.resolve("Botafogo")
        displays = [t.display for t in teams]
        assert displays[0] == "Botafogo"
        assert "Botafogo-PB" in displays and "Botafogo-SP" in displays

    def test_america_disambiguation(self, registry):
        teams = registry.resolve("America")
        assert teams[0].display == "América-MG"
        assert any(t.display == "América-RN" for t in teams)

    def test_compact_substring(self, registry):
        assert registry.resolve("saopaulo")[0].display == "São Paulo"
        assert registry.resolve("inter")[0].display == "Internacional"

    def test_stateless_merge_gremio(self, registry):
        """'Grêmio' (stateless) merges into Grêmio-RS, not a new entity."""
        team = registry.resolve("Grêmio")[0]
        assert team.region == "RS"

    def test_different_clubs_stay_distinct(self, registry):
        """Same base, different states -> separate entities."""
        keys = {t.key for t in registry.resolve("Botafogo")}
        assert "botafogo|RJ" in keys and "botafogo|PB" in keys
        # América-MG vs América-RN
        keys = {t.key for t in registry.resolve("América")}
        assert "america|MG" in keys and "america|RN" in keys
        # Internacional-RS vs Internacional-SC (Inter de Lages)
        keys = {t.key for t in registry.resolve("Internacional")}
        assert "internacional|RS" in keys and "internacional|SC" in keys

    def test_unresolved_query(self, registry):
        assert registry.resolve("zzz nonexistent qqq") == []

    def test_strict_resolution_rejects_substring(self, registry):
        """FIFA club 'Inter' must NOT be attributed to Internacional-RS."""
        assert registry.resolve_exact("Inter") is None
        assert registry.resolve_exact("Internacional").key == "internacional|RS"


class TestRegistryFromScratch:
    """Scenario: Stateless spelling merges into the most prominent region
    Given one stateless name and one regional name for the same base
    Then they collapse into a single entity
    """

    def test_stateless_merge(self):
        reg = TeamRegistry()
        reg.add_name("Grêmio", 5)
        reg.add_name("Grêmio - RS", 10)
        reg.add_name("Gremio RS", 3)
        reg.finalize()
        teams = reg.resolve("Grêmio")
        assert len(teams) == 1
        assert teams[0].region == "RS"
        assert teams[0].match_count == 18

    def test_ambiguous_regions_stay_apart(self):
        reg = TeamRegistry()
        reg.add_name("Botafogo-RJ", 100)
        reg.add_name("Botafogo-PB", 20)
        reg.finalize()
        assert len(reg.resolve("Botafogo")) == 2

    def test_display_names(self, registry):
        assert registry.display_name("flamengo", "RJ") == "Flamengo"
        assert registry.display_name("sao paulo", "SP") == "São Paulo"
        assert registry.display_name("atletico", "MG") == "Atlético-MG"
