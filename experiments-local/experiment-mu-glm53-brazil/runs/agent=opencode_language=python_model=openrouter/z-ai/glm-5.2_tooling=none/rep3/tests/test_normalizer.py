"""BDD tests for team-name normalization (normalizer.py).

Context block
-------------
Feature: Team Name Normalization
  The datasets use mixed naming conventions ("Palmeiras-SP", "Palmeiras",
  "Sociedade Esportiva Palmeiras"). Normalization must collapse these to
  one canonical entity so head-to-head and standings are correct.
"""
from __future__ import annotations

from normalizer import canonical_name, name_key, teams_match


class TestCanonicalName:
    # Scenario: state suffix "-SP" is stripped
    def test_strips_state_suffix_compact(self):
        # Given a name "Palmeiras-SP"
        # When normalized
        # Then the "-SP" suffix is removed
        assert canonical_name("Palmeiras-SP") == "Palmeiras"

    # Scenario: state suffix " - RJ" (spaced) is stripped
    def test_strips_state_suffix_spaced(self):
        assert canonical_name("Flamengo - RJ") == "Flamengo"

    # Scenario: parenthetical alias is dropped (Copa do Brasil quirk)
    def test_strips_parenthetical(self):
        raw = "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"
        assert "antigo" not in canonical_name(raw)
        assert canonical_name(raw) == "Boavista"

    # Scenario: country tag in Libertadores is stripped
    def test_strips_country_tag(self):
        assert canonical_name("Barcelona-EQU") == "Barcelona"

    # Scenario: legal suffix "Sport Club" is removed
    def test_strips_legal_suffix(self):
        assert canonical_name("Corinthians Sport Club") == "Corinthians"

    # Scenario: accents are preserved in display name
    def test_preserves_accents(self):
        assert canonical_name("Grêmio-RS") == "Grêmio"


class TestNameKey:
    # Scenario: accent folding for equality
    def test_folds_accents(self):
        assert name_key("São Paulo") == name_key("Sao Paulo")

    # Scenario: different raw forms of same team share a key
    def test_same_team_same_key(self):
        assert name_key("Palmeiras-SP") == name_key("Palmeiras") == name_key("Sociedade Esportiva Palmeiras")


class TestTeamsMatch:
    # Scenario: equivalent names match
    def test_match_equivalent(self):
        assert teams_match("Flamengo-RJ", "Flamengo")

    # Scenario: different teams do not match
    def test_no_match_different(self):
        assert not teams_match("Flamengo", "Fluminense")

    # Scenario: empty strings never match
    def test_empty_never_matches(self):
        assert not teams_match("", "")
