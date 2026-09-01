"""BDD scenarios for team-name and date normalization (TASK.md "Data Quality Notes").

Feature: Team name variation handling
  The datasets spell one club in many ways. The normalizer must map every
  spelling of a club to a single canonical key so that matches, players and
  queries join correctly across all six CSV files.
"""

from __future__ import annotations

import pytest

from normalize import (
    canonical_team_key,
    parse_date,
    parse_int,
    resolve_competition,
    team_display_name,
)


class TestTeamNameVariations:
    """Scenarios: identical clubs spelled differently across the files."""

    def test_state_suffix_styles_are_equivalent(self):
        """
        Scenario: state-suffix variations
          Given names "Palmeiras-SP", "Palmeiras - SP" and "Palmeiras"
          When each is normalized
          Then all produce the same canonical key
        """
        # Given / When
        keys = {
            canonical_team_key("Palmeiras-SP"),
            canonical_team_key("Palmeiras - SP"),
            canonical_team_key("palmeiras"),
        }
        # Then
        assert keys == {"palmeiras-sp"}

    def test_full_official_names_map_to_the_same_club(self):
        """
        Scenario: official long names
          Given the FIFA name "Sport Club do Recife" and the league name
            "Sport-PE"
          When each is normalized
          Then both resolve to the Recife club
        """
        assert canonical_team_key("Sport Club do Recife") == "sport-pe"
        assert canonical_team_key("Sport-PE") == "sport-pe"
        assert canonical_team_key("Sport Recife") == "sport-pe"

    def test_accents_and_case_do_not_matter(self):
        """
        Scenario: accents and casing
          Given "Grêmio", "Gremio" and "GREMIO"
          When normalized
          Then all map to the same key
        """
        assert (
            canonical_team_key("Grêmio")
            == canonical_team_key("Gremio")
            == canonical_team_key("GREMIO")
            == "gremio-rs"
        )

    def test_athletico_vs_atletico_paranaense_unify(self):
        """
        Scenario: pre/post-2019 rebrand of Athletico-PR
          Given "Atlético-PR", "Athletico Paranaense" and the bare
            Libertadores spelling "Athletico"
          When normalized
          Then all map to the Paranaense club
        """
        assert canonical_team_key("Atlético-PR") == "atletico-pr"
        assert canonical_team_key("Athletico Paranaense") == "atletico-pr"
        assert canonical_team_key("Athletico") == "atletico-pr"

    def test_atletico_mineiro_long_name(self):
        """
        Scenario: FIFA long name for Atlético Mineiro
          Given "Atlético Mineiro" and "Atletico-MG"
          When normalized
          Then both map to the Belo Horizonte club
        """
        assert canonical_team_key("Atlético Mineiro") == "atletico-mg"
        assert canonical_team_key("Atletico-MG") == "atletico-mg"

    def test_homonym_clubs_stay_distinct(self):
        """
        Scenario: same base name in different states
          Given Vasco da Gama (RJ) and the FIFA club "Atlético Madrid"
          When normalized alongside their Brazilian homonyms
          Then the distinct clubs keep distinct keys
        """
        assert canonical_team_key("Vasco") == "vasco-rj"
        assert canonical_team_key("Vasco da Gama") == "vasco-rj"
        assert canonical_team_key("América - MG") == "america-mg"
        assert canonical_team_key("América de Natal - RN") == "america-rn"
        assert canonical_team_key("Santos - AP") == "santos-ap"
        assert canonical_team_key("Santos - SP") == "santos-sp"
        assert canonical_team_key("Santos") == "santos-sp"

    def test_dotted_abbreviations_collapse(self):
        """
        Scenario: dotted club abbreviations
          Given "A.s.a. - AL" and "Asa - AL"
          When normalized
          Then both map to the same Alagoas club key
          And "A.b.c. - RN" equals "ABC - RN"
        """
        assert canonical_team_key("A.s.a. - AL") == canonical_team_key("Asa - AL")
        assert canonical_team_key("Asa - AL") == "asa-al"
        assert canonical_team_key("A.b.c. - RN") == canonical_team_key("ABC - RN")

    def test_international_country_codes_are_kept(self):
        """
        Scenario: Libertadores international clubs
          Given "Nacional (URU)" and "Nacional-URU"
          When normalized
          Then both keep their country suffix and stay distinct from
            Nacional-PAR
        """
        assert canonical_team_key("Nacional (URU)") == "nacional-uru"
        assert canonical_team_key("Nacional-URU") == "nacional-uru"
        assert canonical_team_key("Nacional (PAR)") == "nacional-par"


class TestDateParsing:
    """Scenarios: the three date formats found in the datasets."""

    def test_iso_date(self):
        """
        Scenario: ISO date
          Given "2023-09-24"
          When parsed
          Then it yields September 24th 2023
        """
        assert parse_date("2023-09-24").isoformat() == "2023-09-24"

    def test_iso_datetime(self):
        """
        Scenario: ISO date with kick-off time
          Given "2012-05-19 18:30:00"
          When parsed
          Then the date part is returned
        """
        assert parse_date("2012-05-19 18:30:00").isoformat() == "2012-05-19"

    def test_brazilian_format(self):
        """
        Scenario: Brazilian DD/MM/YYYY dates (historical file)
          Given "29/03/2003"
          When parsed
          Then it yields March 29th 2003
        """
        assert parse_date("29/03/2003").isoformat() == "2003-03-29"

    def test_missing_values(self):
        """
        Scenario: null markers in the Libertadores file
          Given "NA", "-" and ""
          When parsed
          Then None is returned instead of raising
        """
        assert parse_date("NA") is None
        assert parse_date("-") is None
        assert parse_date("") is None
        assert parse_int("-") is None
        assert parse_int("NA") is None

    def test_goals_parse_from_strings(self):
        """
        Scenario: goals stored as text
          Given the string "2"
          When parsed
          Then the integer 2 is returned
        """
        assert parse_int("2") == 2
        assert parse_int(3) == 3


class TestCompetitionAliases:
    """Scenarios: free-text competition names."""

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("brasileirao", "Brasileirão Série A"),
            ("Serie A", "Brasileirão Série A"),
            ("campeonato brasileiro", "Brasileirão Série A"),
            ("serie b", "Brasileirão Série B"),
            ("copa do brasil", "Copa do Brasil"),
            ("brazilian cup", "Copa do Brasil"),
            ("libertadores", "Copa Libertadores"),
        ],
    )
    def test_alias_resolution(self, raw, expected):
        """
        Scenario: competition aliases
          Given a user-typed competition name
          When resolved
          Then it maps to the canonical competition
        """
        assert resolve_competition(raw) == expected

    def test_unknown_competition(self):
        """
        Scenario: unknown competition
          Given "Premier League"
          When resolved
          Then None is returned
        """
        assert resolve_competition("Premier League") is None


class TestDisplayNames:
    """Scenario: canonical keys render as readable names."""

    def test_display_for_major_clubs(self):
        assert team_display_name("flamengo-rj") == "Flamengo"
        assert team_display_name("sao paulo-sp") == "São Paulo"
        assert team_display_name("gremio-rs") == "Grêmio"

    def test_display_fallback_for_small_clubs(self):
        assert team_display_name("altos-pi") == "Altos (PI)"
