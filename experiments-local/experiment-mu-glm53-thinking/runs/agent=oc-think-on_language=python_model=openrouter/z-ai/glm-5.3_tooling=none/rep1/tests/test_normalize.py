"""Feature: Data quality - team name variations, date formats, encoding.

Scenarios covering the TASK.md "Data Quality Notes": state suffixes,
accents/cedillas (UTF-8), full legal names, FIFA-style names, country tags,
Brazilian vs ISO date formats and money parsing.
"""

from __future__ import annotations

import datetime as dt

from brazilian_soccer.dates import parse_date, parse_int, parse_money_eur
from brazilian_soccer.normalize import (
    DERBIES,
    competition_label,
    display_name,
    fold_text,
    team_key,
)


class TestTeamNameVariations:
    """Feature: Team name normalization."""

    def test_state_suffix_and_bare_name_are_the_same_club(self):
        """Scenario: Palmeiras spelled with and without state suffix."""
        # Given team names with different state-suffix conventions
        # When they are normalized
        # Then they resolve to the same canonical key
        assert team_key("Palmeiras-SP") == team_key("Palmeiras") == "palmeiras"
        assert team_key("Flamengo-RJ") == team_key("Flamengo") == "flamengo"

    def test_accented_and_unaccented_spellings_are_the_same_club(self):
        """Scenario: accented vs unaccented spellings across files."""
        # Given files store 'São Paulo-SP' and 'Sao Paulo' (accents stripped)
        # When they are normalized
        # Then they resolve to the same club
        assert team_key("São Paulo-SP") == team_key("Sao Paulo") == "sao paulo"
        assert team_key("Grêmio") == team_key("Gremio-RS") == "gremio"
        assert team_key("Atlético-MG") == team_key("Atletico-MG") == "atletico-mg"
        assert team_key("Avaí-SC") == team_key("Avai-SC") == "avai"

    def test_full_legal_name_resolves_to_the_short_name(self):
        """Scenario: full club names."""
        # Given the official long form of a club name
        # When it is normalized
        # Then it matches the short form used in match files
        assert team_key("Sport Club Corinthians Paulista") == "corinthians"
        assert team_key("Fortaleza Esporte Clube") == "fortaleza"
        assert team_key("Sociedade Esportiva Palmeiras") == "palmeiras"

    def test_fifa_style_names_resolve_to_match_file_names(self):
        """Scenario: FIFA database club names."""
        # Given FIFA uses 'Atlético Paranaense' and 'América FC (Minas Gerais)'
        # When normalized
        # Then they match the match-data spellings
        assert team_key("Atlético Paranaense") == team_key("Athletico-PR") == "athletico-pr"
        assert team_key("Atletico-PR") == "athletico-pr"
        assert team_key("Athletico Paranaense") == "athletico-pr"
        assert team_key("América FC (Minas Gerais)") == team_key("América-MG") == "america-mg"
        assert team_key("Atlético Mineiro") == "atletico-mg"
        assert team_key("Sport Club do Recife") == team_key("Sport-PE") == "sport"
        assert team_key("Ceará Sporting Club") == team_key("Ceara-CE") == "ceara"

    def test_same_base_different_state_stay_distinct(self):
        """Scenario: clubs sharing a name but from different states."""
        # Given Serie C has small clubs named like famous clubs
        # When normalized
        # Then they stay distinct from the famous club
        assert team_key("Flamengo-PI") != "flamengo"
        assert team_key("Santos-AP") != "santos"
        assert team_key("Botafogo PB") != "botafogo"
        assert team_key("Atletico-GO") == "atletico-go"
        assert team_key("América-RN") == "america-rn"
        assert team_key("América-MG") == "america-mg"

    def test_libertadores_country_tags_are_handled(self):
        """Scenario: foreign clubs with country tags."""
        # Given Libertadores names like 'Barcelona-EQU' and 'Nacional (URU)'
        # When normalized
        # Then foreign clubs keep their country and stay distinct
        assert team_key("Nacional (URU)") == team_key("Nacional-URU") == "nacional-uru"
        assert team_key("Barcelona-EQU") == "barcelona-equ"
        assert team_key("Guaraní (PAR)") == team_key("Guaraní-PAR") == "guarani-par"
        assert team_key("Barcelona-EQU") != team_key("FC Barcelona")

    def test_similar_foreign_clubs_stay_distinct(self):
        """Scenario: clubs with similar names."""
        assert team_key("Santos Laguna") != team_key("Santos")
        assert team_key("Vitória Guimarães") != team_key("Vitória-BA")
        assert team_key("Atlético Madrid") != "atletico-mg"

    def test_display_names_keep_portuguese_accents(self):
        """Scenario: canonical display names are human-friendly."""
        assert display_name("sao paulo") == "São Paulo"
        assert display_name("gremio") == "Grêmio"
        assert display_name("vitoria") == "Vitória"
        assert display_name("goias") == "Goiás"
        assert display_name("athletico-pr") == "Athletico-PR"

    def test_fold_text_is_case_and_accent_insensitive(self):
        """Scenario: UTF-8 search folding."""
        assert fold_text("São Paulo") == fold_text("sao paulo") == "sao paulo"
        assert fold_text("Grêmio") == "gremio"


class TestDateFormats:
    """Feature: Date format normalization."""

    def test_iso_datetime_with_time(self):
        # Given '2012-05-19 18:30:00'
        # When parsed
        # Then the calendar date is correct
        assert parse_date("2012-05-19 18:30:00") == dt.date(2012, 5, 19)

    def test_plain_iso_date(self):
        assert parse_date("2023-09-24") == dt.date(2023, 9, 24)

    def test_brazilian_format(self):
        # Given '29/03/2003' (DD/MM/YYYY from the historical file)
        # When parsed
        # Then it is March 29th, not the 3rd of the 29th month
        assert parse_date("29/03/2003") == dt.date(2003, 3, 29)

    def test_missing_markers_become_none(self):
        # Given 'NA', '-' and empty strings
        # When parsed
        # Then they are treated as unknown
        assert parse_date("NA") is None
        assert parse_date("-") is None
        assert parse_date("") is None
        assert parse_date(None) is None

    def test_goal_parsing_handles_na_and_floats(self):
        assert parse_int("NA") is None
        assert parse_int("-") is None
        assert parse_int("2") == 2
        assert parse_int("1.0") == 1

    def test_money_parsing(self):
        assert parse_money_eur("€110.5M") == 110_500_000
        assert parse_money_eur("€565K") == 565_000
        assert parse_money_eur("NA") is None


class TestCompetitionLabels:
    """Feature: Competition name normalization."""

    def test_common_spellings_resolve(self):
        assert competition_label("brasileirão") == "Brasileirão Série A"
        assert competition_label("Serie A") == "Brasileirão Série A"
        assert competition_label("campeonato brasileiro") == "Brasileirão Série A"
        assert competition_label("serie b") == "Brasileirão Série B"
        assert competition_label("Copa do Brasil") == "Copa do Brasil"
        assert competition_label("libertadores") == "Copa Libertadores"

    def test_unknown_competition_is_rejected(self):
        assert competition_label("Champions League") is None


class TestDerbyRegistry:
    """Feature: rivalry registry used by derby queries."""

    def test_named_derbies_map_to_canonical_teams(self):
        assert DERBIES["Fla-Flu"] == ("flamengo", "fluminense")
        assert DERBIES["Gre-Nal"] == ("gremio", "internacional")
        assert DERBIES["Derby Paulista"] == ("corinthians", "palmeiras")
        assert len(DERBIES) >= 10
