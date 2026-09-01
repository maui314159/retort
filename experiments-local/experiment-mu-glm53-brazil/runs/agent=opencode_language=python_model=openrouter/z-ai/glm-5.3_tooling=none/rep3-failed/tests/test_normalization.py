"""BDD scenarios for team-name normalization.

Feature: Team Name Normalization
  The datasets spell club names in many ways (state suffixes, accents,
  full legal names, nicknames).  Every variant must resolve to the same
  canonical team so cross-file queries work.
"""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp.normalize import TeamNotFoundError


class TestStateSuffixVariants:
    """
    Scenario: State-suffixed and bare names are the same team
      Given the match data is loaded
      When I canonicalize "Palmeiras-SP", "Palmeiras" and "Palmeiras SP"
      Then all three resolve to the same canonical key
    """

    def test_given_match_data_when_canonicalizing_palmeiras_variants_then_keys_match(self, registry):
        keys = {
            registry.canonical_key("Palmeiras-SP"),
            registry.canonical_key("Palmeiras"),
            registry.canonical_key("Palmeiras SP"),
            registry.canonical_key("Palmeiras - SP"),
        }
        assert keys == {"palmeiras"}

    def test_given_accents_when_canonicalizing_gremio_variants_then_keys_match(self, registry):
        keys = {
            registry.canonical_key("Grêmio"),
            registry.canonical_key("Gremio"),
            registry.canonical_key("Gremio RS"),
            registry.canonical_key("Grêmio - RS"),
        }
        assert keys == {"gremio"}


class TestAmbiguousBaseNames:
    """
    Scenario: Ambiguous base names keep their state discriminator
      Given the match data is loaded
      When I canonicalize "Atletico-MG" and "Atletico-PR"
      Then they resolve to different canonical keys
      And "Atlético Mineiro" resolves to the Atlético-MG key
    """

    def test_when_canonicalizing_atletico_variants_then_states_disambiguate(self, registry):
        assert registry.canonical_key("Atletico-MG") == "atletico-mg"
        assert registry.canonical_key("Atletico-PR") == "atletico-pr"
        assert registry.canonical_key("Atlético - PR") == "atletico-pr"

    def test_when_canonicalizing_full_names_then_alias_applies(self, registry):
        assert registry.canonical_key("Atlético Mineiro") == "atletico-mg"
        assert registry.canonical_key("Atletico Paranaense") == "atletico-pr"
        assert registry.canonical_key("Athletico") == "atletico-pr"

    def test_when_canonicalizing_botafogo_variants_then_three_clubs_stay_distinct(self, registry):
        keys = {
            registry.canonical_key("Botafogo"),
            registry.canonical_key("Botafogo RJ"),
            registry.canonical_key("Botafogo PB"),
            registry.canonical_key("Botafogo SP"),
        }
        assert keys == {"botafogo-rj", "botafogo-pb", "botafogo-sp"}

    def test_when_a_bare_ambiguous_name_is_resolved_then_the_most_common_variant_wins(self, registry):
        key, display = registry.resolve("Botafogo")
        assert key == "botafogo-rj"
        key, display = registry.resolve("Santos")
        assert key == "santos-sp"


class TestFullNamesAndNicknames:
    """
    Scenario: Full legal names and nicknames resolve
      Given the match data is loaded
      When I resolve "Sport Club Corinthians Paulista" and "Timão"
      Then both resolve to Corinthians
    """

    def test_when_resolving_full_legal_name_then_it_matches_the_short_name(self, registry):
        assert registry.resolve("Sport Club Corinthians Paulista")[0] == "corinthians"
        assert registry.resolve("SC Corinthians Paulista")[0] == "corinthians"

    def test_when_resolving_nicknames_then_they_map_to_known_clubs(self, registry):
        assert registry.resolve("Timão")[0] == "corinthians"
        assert registry.resolve("fla")[0] == "flamengo-rj"
        assert registry.resolve("Verdão")[0] == "palmeiras"

    def test_when_resolving_vasco_variants_then_they_merge(self, registry):
        keys = {
            registry.canonical_key("Vasco"),
            registry.canonical_key("Vasco da Gama-RJ"),
            registry.canonical_key("Vasco Da Gama RJ"),
        }
        assert keys == {"vasco da gama"}


class TestForeignClubs:
    """
    Scenario: Foreign clubs with country suffixes stay distinct
      Given the Libertadores data is loaded
      When I canonicalize "Nacional (URU)" and "Nacional (PAR)"
      Then they resolve to different canonical keys
    """

    def test_when_canonicalizing_foreign_suffixes_then_countries_disambiguate(self, registry):
        assert registry.canonical_key("Nacional (URU)") == "nacional-uru"
        assert registry.canonical_key("Nacional (PAR)") == "nacional-par"
        assert registry.canonical_key("Barcelona-EQU") == "barcelona"


class TestFifaClubNames:
    """
    Scenario: FIFA club names map onto match-data teams
      Given the FIFA dataset is loaded
      When I canonicalize "Ceará Sporting Club" and "Sport Club do Recife"
      Then they resolve to the same keys used by the match data
    """

    def test_when_canonicalizing_fifa_club_names_then_they_match_match_data_keys(self, registry):
        assert registry.canonical_key("Ceará Sporting Club") == "ceara"
        assert registry.canonical_key("Sport Club do Recife") == "sport"
        assert registry.canonical_key("América FC (Minas Gerais)") == "america-mg"
        assert registry.canonical_key("EC Bahia") == "bahia"
        assert registry.canonical_key("Fortaleza FC") == "fortaleza"
        assert registry.canonical_key("Atlético Goianiense") == "atletico-go"


class TestUnresolvableNames:
    """
    Scenario: Unknown team names produce suggestions
      Given the match data is loaded
      When I resolve a name that matches nothing
      Then a TeamNotFoundError is raised with suggestions
    """

    def test_when_resolving_an_unknown_name_then_an_error_with_suggestions_is_raised(self, registry):
        with pytest.raises(TeamNotFoundError):
            registry.resolve("Real Madrid Castilla B")

    def test_when_resolving_a_misspelled_name_then_fuzzy_matching_helps(self, registry):
        key, _ = registry.resolve("Palmeirass")
        assert key == "palmeiras"


class TestHistoricalClubMerges:
    """
    Scenario: Renamed clubs merge under one key
      Given the match data is loaded
      When I canonicalize "Bragantino" and "Red Bull Bragantino-SP"
      Then both resolve to the same canonical key
    """

    def test_when_canonicalizing_bragantino_then_historical_and_modern_names_merge(self, registry):
        assert registry.canonical_key("Bragantino") == "red bull bragantino"
        assert registry.canonical_key("Red Bull Bragantino-SP") == "red bull bragantino"
