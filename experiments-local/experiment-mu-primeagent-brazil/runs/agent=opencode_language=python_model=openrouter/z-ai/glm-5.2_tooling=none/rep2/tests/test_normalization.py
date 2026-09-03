"""BDD tests: team-name normalization handles dataset variations.

Feature: Team Name Normalization
  The datasets spell the same club many different ways. The normalizer must
  collapse those variations into a single canonical key while preserving the
  Brazilian state / foreign country for disambiguation.
"""
from __future__ import annotations

from brsl.normalization import normalize_team, team_matches


class TestTeamNameNormalization:
    # Scenario: stripping a Brazilian state suffix
    def test_state_suffix_is_stripped(self):
        # Given a name "Palmeiras-SP"
        # When it is normalized
        # Then the display is "Palmeiras" and the state is "SP"
        t = normalize_team("Palmeiras-SP")
        assert t.display == "Palmeiras"
        assert t.key == "palmeiras"
        assert t.state == "SP"
        assert t.country is None

    # Scenario: accented and unaccented variants share a key
    def test_accents_are_canonicalized(self):
        # Given "Sao Paulo" and "São Paulo"
        # When both are normalized
        # Then their keys are equal
        assert normalize_team("Sao Paulo").key == normalize_team("São Paulo").key

    # Scenario: foreign club country codes are captured
    def test_country_code_in_parens(self):
        # Given "Nacional (URU)"
        # When normalized
        # Then the country is "URU" and the key is "nacional"
        t = normalize_team("Nacional (URU)")
        assert t.country == "URU"
        assert t.key == "nacional"

    def test_country_code_dash_suffix(self):
        t = normalize_team("Barcelona-EQU")
        assert t.country == "EQU"
        assert t.key == "barcelona"

    # Scenario: a leading "FC" prefix is removed from the display name
    def test_leading_fc_prefix(self):
        t = normalize_team("FC Barcelona")
        assert t.display == "Barcelona"
        assert t.key == "barcelona"

    # Scenario: the distinctive leading word "Sport" is preserved
    def test_sport_not_stripped(self):
        # Given "Sport Club do Recife" (the club Sport)
        # When normalized
        # Then the key still contains "sport" so it can match the team "Sport"
        assert "sport" in normalize_team("Sport Club do Recife").key.split()
        assert normalize_team("Sport").key == "sport"

    # Scenario: ambiguous query matches a longer candidate name
    def test_team_matches_substring(self):
        assert team_matches("Sport", "Sport Club do Recife")
        assert team_matches("Barcelona", "FC Barcelona")
        assert team_matches("Flamengo", "Flamengo-RJ")

    def test_team_matches_handles_accented_variants(self):
        assert team_matches("Sao Paulo", "São Paulo")
        assert team_matches("Gremio", "Grêmio")

    def test_non_matching_team(self):
        assert not team_matches("Flamengo", "Palmeiras")
