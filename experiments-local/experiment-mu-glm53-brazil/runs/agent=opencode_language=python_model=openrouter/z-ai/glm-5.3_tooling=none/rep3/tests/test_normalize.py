"""
BDD GWT scenarios: name, date, number and competition normalization.

Gherkin counterpart: ``tests/features/normalization.feature``.

Covers TASK.md "Data Quality Notes": team-name variations, date formats,
UTF-8/accent handling, plus competition-name resolution used by every
query tool.
"""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp.normalize import (
    fold_accents,
    normalize_team,
    parse_date,
    parse_int,
    resolve_competition,
)


class TestTeamNameNormalization:
    def test_given_a_state_suffixed_name_when_normalized_then_state_is_split(self):
        # Given the name "Palmeiras-SP" from Brasileirao_Matches.csv
        # When the name is normalized
        team = normalize_team("Palmeiras-SP")
        # Then the base is "palmeiras" and the state is "SP"
        assert team.base == "palmeiras"
        assert team.state == "SP"
        assert team.key == "palmeiras|SP"

    def test_given_a_spaced_state_suffix_when_normalized_then_state_is_split(self):
        # Given "América - MG" from Brazilian_Cup_Matches.csv
        team = normalize_team("América - MG")
        # Then the accent is folded and the state lifted out
        assert team.base == "america"
        assert team.state == "MG"

    def test_given_an_accented_name_when_normalized_then_ascii_base(self):
        # Given "São Paulo" and "Grêmio" (UTF-8 accented spellings)
        # When normalized
        # Then the base folds to ASCII without changing identity
        assert normalize_team("São Paulo").base == "saopaulo"
        assert normalize_team("Grêmio").base == "gremio"
        assert fold_accents("Avaí") == "Avai"

    def test_given_a_full_official_name_when_normalized_then_alias_applies(self):
        # Given "Sport Club do Recife" (FIFA spelling)
        # When normalized
        team = normalize_team("Sport Club do Recife")
        # Then it maps onto the canonical Sport-PE identity
        assert team.key == "sport|PE"

    def test_given_vasco_spellings_when_normalized_then_same_identity(self):
        # Given "Vasco da Gama" and "Vasco" as seen across files
        # When both are normalized
        full = normalize_team("Vasco da Gama-RJ")
        short = normalize_team("Vasco")
        # Then both resolve to the vasco|RJ club key space
        assert full.key == "vasco|RJ"
        assert short.base == "vasco"

    def test_given_athletico_spellings_when_normalized_then_atletico_pr(self):
        # Given the 2019 rebrand spellings of the Paranaense club
        # When normalized with and without a state suffix
        # Then all map to the same atletico|PR identity
        assert normalize_team("Athletico-PR").key == "atletico|PR"
        assert normalize_team("Athletico").key == "atletico|PR"
        assert normalize_team("Athletico Paranaense - PR").key == "atletico|PR"

    def test_given_atletico_mineiro_when_normalized_then_atletico_mg(self):
        # Given "Atlético Mineiro - MG" and bare "Atlético Mineiro"
        # When normalized
        # Then both give the atletico|MG identity
        assert normalize_team("Atlético Mineiro - MG").key == "atletico|MG"
        assert normalize_team("Atlético Mineiro").key == "atletico|MG"

    def test_given_parenthetical_names_when_normalized_then_content_kept(self):
        # Given foreign qualifiers that must stay distinct
        nacional_uru = normalize_team("Nacional (URU)")
        nacional_par = normalize_team("Nacional (PAR)")
        # Then the two clubs do not collapse together
        assert nacional_uru.base != nacional_par.base
        assert nacional_uru.base == "nacionaluru"
        assert nacional_par.base == "nacionalpar"

    def test_given_a_bare_name_when_normalized_then_no_state(self):
        # Given "Fortaleza" (no suffix) from the Libertadores file
        team = normalize_team("Fortaleza")
        # Then the state is None and the key ends with the separator
        assert team.state is None
        assert team.key == "fortaleza|"


class TestDateParsing:
    def test_given_iso_date_with_time_when_parsed_then_date(self):
        # Given "2012-05-19 18:30:00" from Brasileirao_Matches.csv
        # When parsed
        # Then the calendar date is returned
        assert parse_date("2012-05-19 18:30:00").isoformat() == "2012-05-19"

    def test_given_plain_iso_date_when_parsed_then_date(self):
        # Given "2023-09-24" from BR-Football-Dataset.csv
        assert parse_date("2023-09-24").isoformat() == "2023-09-24"

    def test_given_brazilian_format_when_parsed_then_date(self):
        # Given "29/03/2003" from novo_campeonato_brasileiro.csv
        # When parsed as DD/MM/YYYY
        # Then March 29th 2003 is returned (not September 29th)
        assert parse_date("29/03/2003").isoformat() == "2003-03-29"

    def test_given_na_or_blank_when_parsed_then_none(self):
        # Given the "NA" placeholders present in the raw data
        assert parse_date("NA") is None
        assert parse_date("") is None
        assert parse_date(None) is None


class TestNumberParsing:
    def test_given_integer_string_when_parsed_then_int(self):
        assert parse_int("2") == 2

    def test_given_float_string_when_parsed_then_int(self):
        # Given BR-Football's "1.0"-style goal columns
        assert parse_int("1.0") == 1
        assert parse_int(2.0) == 2

    def test_given_na_when_parsed_then_none(self):
        assert parse_int("NA") is None
        assert parse_int("-") is None
        assert parse_int("") is None


class TestCompetitionResolution:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("Brasileirão Serie A", "Brasileirão Serie A"),
            ("serie a", "Brasileirão Serie A"),
            ("brasileirão", "Brasileirão Serie A"),
            ("Serie B", "Brasileirão Serie B"),
            ("Serie C", "Brasileirão Serie C"),
            ("Copa do Brasil", "Copa do Brasil"),
            ("cdb", "Copa do Brasil"),
            ("Libertadores", "Copa Libertadores"),
            ("copa libertadores", "Copa Libertadores"),
        ],
    )
    def test_given_free_text_competition_when_resolved_then_canonical(self, raw, expected):
        # Given a user-typed competition name
        # When resolved
        # Then the canonical competition name is returned
        assert resolve_competition(raw) == expected

    def test_given_unknown_competition_when_resolved_then_none(self):
        assert resolve_competition("Champions League") is None
        assert resolve_competition(None) is None
