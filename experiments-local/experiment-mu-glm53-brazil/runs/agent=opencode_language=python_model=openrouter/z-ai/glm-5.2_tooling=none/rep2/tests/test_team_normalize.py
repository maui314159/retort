# SPDX-License-Identifier: Apache-2.0
# Context block ----------------------------------------------------------------
# BDD tests for the team-name normalization layer.
# Style: Given/When/Then prose comments inside each test, mirroring the
# Gherkin scenarios in the TASK.md testing section.
# --------------------------------------------------------------------------- #
"""BDD scenarios for team name normalization."""

from brazilian_soccer_mcp.team_normalize import is_derby, normalize_team


class TestNormalizeTeam:
    def test_strips_state_suffix(self):
        # Given a team name with the "-SP" state suffix
        # When I normalize "Palmeiras-SP"
        # Then I receive the canonical key "palmeiras"
        assert normalize_team("Palmeiras-SP") == "palmeiras"

    def test_strips_parens_country(self):
        # Given a Libertadores name with "(URU)" country tag
        # When I normalize "Nacional (URU)"
        # Then I receive "nacional-uru"
        assert normalize_team("Nacional (URU)") == "nacional-uru"

    def test_strips_accents(self):
        # Given an accented club name "Grêmio"
        # When I normalize it
        # Then the key is ASCII-only "gremio"
        assert normalize_team("Grêmio") == "gremio"

    def test_full_name_resolves_to_canonical(self):
        # Given a FIFA full-name variant "Clube de Regatas do Flamengo"
        # When I normalize it
        # Then it resolves to the same key as "Flamengo"
        assert normalize_team("Clube de Regatas do Flamengo") == "flamengo"
        assert normalize_team("Flamengo") == "flamengo"

    def test_fifa_atletico_mineiro_resolves(self):
        # Given FIFA's "Atlético Mineiro"
        # When I normalize it
        # Then it resolves to the Atletico-MG key used by the match files
        assert normalize_team("Atlético Mineiro") == "atletico-mg"

    def test_fifa_ceara_sporting_club_resolves(self):
        # Given FIFA's "Ceará Sporting Club"
        # When I normalize it
        # Then it resolves to "ceara"
        assert normalize_team("Ceará Sporting Club") == "ceara"

    def test_dash_separator_with_spaces(self):
        # Given the "América - MG" form from Brazilian_Cup_Matches
        # When I normalize it
        # Then it resolves to "america-mg"
        assert normalize_team("América - MG") == "america-mg"

    def test_empty_input_returns_empty(self):
        assert normalize_team("") == ""
        assert normalize_team(None) == ""  # type: ignore[arg-type]


class TestDerbies:
    def test_fla_flu_is_derby(self):
        # Given the traditional Fla-Flu pairing
        # When I check whether Flamengo vs Fluminense is a derby
        # Then it is True
        assert is_derby("Flamengo", "Fluminense") is True

    def test_grenal_is_derby(self):
        assert is_derby("Grêmio", "Internacional") is True

    def test_non_derby_returns_false(self):
        # Given two unrelated clubs
        # When I check Flamengo vs Barcelona
        # Then it is False
        assert is_derby("Flamengo", "Barcelona") is False

    def test_derby_check_is_order_independent(self):
        assert is_derby("Palmeiras", "Corinthians") is is_derby("Corinthians", "Palmeiras")
