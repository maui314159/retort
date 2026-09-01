"""Feature: Data Loading and Normalization

Background:
    Given the six CSV datasets in data/kaggle
    And the datasets use different team naming conventions and date formats
    And Brazilian Portuguese text contains accents and cedillas
"""

from __future__ import annotations

from datetime import date

from brazilian_soccer.data import (
    COPA_DO_BRASIL,
    LIBERTADORES,
    SERIE_A,
    SOURCE_BRASILEIRAO,
    SOURCE_BRFB,
    SOURCE_CUP,
    SOURCE_FIFA,
    SOURCE_LIBERTADORES,
    SOURCE_NOVO,
)
from brazilian_soccer.normalize import parse_date, team_key


class TestAllSixFilesAreLoadable:
    """Scenario: All 6 CSV files are loadable and queryable
        Given the match data is loaded
        Then matches from every source file should be present
        And the FIFA player data should be present
    """

    def test_given_loaded_dataset_when_grouping_by_source_then_all_six_sources_present(self, dataset):
        sources = {m.source for m in dataset.matches}
        assert sources == {
            SOURCE_BRASILEIRAO, SOURCE_CUP, SOURCE_LIBERTADORES,
            SOURCE_BRFB, SOURCE_NOVO,
        }
        assert len(dataset.players) == 18207

    def test_given_loaded_dataset_then_match_and_team_volumes_are_sane(self, dataset):
        assert len(dataset.matches) > 20000
        assert len(dataset.deduped_matches) > 15000
        assert len(dataset.known_teams) > 400


class TestTeamNameVariations:
    """Scenario: Handle team name variations correctly
        Given names like "Palmeiras-SP", "Palmeiras" and full club names
        When I normalize them
        Then they should map to the same canonical team key
    """

    def test_given_state_suffixed_and_plain_names_when_normalized_then_same_key(self):
        assert team_key("Palmeiras-SP") == team_key("Palmeiras") == team_key("palmeiras")
        assert team_key("Flamengo-RJ") == team_key("Flamengo")
        assert team_key("Corinthians-SP") == team_key("Corinthians")
        assert team_key("São Paulo") == team_key("Sao Paulo-SP")

    def test_given_atletico_variants_when_normalized_then_atlético_clubs_stay_distinct(self):
        atletico_mg = {team_key(n) for n in ("Atlético-MG", "Atletico-MG", "Atlético Mineiro", "Atletico Mineiro MG")}
        atletico_pr = {team_key(n) for n in ("Atlético-PR", "Athletico-PR", "Athletico Paranaense", "Athletico")}
        atletico_go = {team_key(n) for n in ("Atlético-GO", "Atletico Goianiense")}
        assert len(atletico_mg) == len(atletico_pr) == len(atletico_go) == 1
        assert atletico_mg != atletico_pr
        assert atletico_mg != atletico_go
        assert atletico_pr != atletico_go

    def test_given_same_base_different_states_when_normalized_then_distinct_keys(self):
        assert team_key("America-MG") != team_key("America-RN")
        assert team_key("Botafogo-RJ") != team_key("Botafogo-PB") != team_key("Botafogo-SP")
        assert team_key("Vitoria-BA") != team_key("Vitoria-ES")

    def test_given_copa_do_brasil_long_names_when_normalized_then_match_serie_a_keys(self):
        assert team_key("Flamengo - RJ") == team_key("Flamengo-RJ")
        assert team_key("Atlético Paranaense - PR") == team_key("Atletico-PR")
        assert team_key("Vasco da Gama - RJ") == team_key("Vasco-RJ")

    def test_given_fifa_club_names_when_normalized_then_match_match_data_keys(self, dataset):
        fifa_brazilian_clubs = [
            "Grêmio", "Santos", "Internacional", "Botafogo", "Fluminense",
            "Cruzeiro", "Bahia", "Atlético Mineiro", "Atlético Paranaense",
            "Ceará Sporting Club", "Sport Club do Recife",
        ]
        for club in fifa_brazilian_clubs:
            assert team_key(club) in dataset.known_teams, club

    def test_given_the_same_fixture_in_multiple_files_when_deduped_then_counted_once(self, dataset):
        flamengo_home_2015 = [
            m for m in dataset.deduped_matches
            if m.competition == SERIE_A and m.season == 2015 and m.home == "flamengo"
        ]
        assert len(flamengo_home_2015) == 19


class TestDateFormats:
    """Scenario: Handle multiple date formats
        Given dates like "2012-05-19 18:30:00", "2023-09-24" and "29/03/2003"
        When I parse them
        Then each should produce the correct date
    """

    def test_given_iso_datetime_when_parsed_then_date_extracted(self):
        assert parse_date("2012-05-19 18:30:00") == date(2012, 5, 19)

    def test_given_iso_date_when_parsed_then_date_extracted(self):
        assert parse_date("2023-09-24") == date(2023, 9, 24)

    def test_given_brazilian_format_when_parsed_then_date_extracted(self):
        assert parse_date("29/03/2003") == date(2003, 3, 29)

    def test_given_garbage_when_parsed_then_none_returned(self):
        assert parse_date("NA") is None
        assert parse_date("") is None
        assert parse_date(None) is None


class TestUtf8Encoding:
    """Scenario: Handle UTF-8 names
        Given Brazilian club names with accents and cedillas
        When they are displayed
        Then the accented forms should be preserved
    """

    def test_given_accented_club_names_when_displayed_then_accents_preserved(self, dataset):
        assert dataset.team_display("sao paulo") == "São Paulo"
        assert dataset.team_display("gremio") == "Grêmio"
        assert dataset.team_display("avai") == "Avaí"
        assert dataset.team_display("coritiba") == "Coritiba"
        assert dataset.team_display("ceara") == "Ceará"
        assert dataset.team_display("vitoria ba") == "Vitória"

    def test_given_accents_in_query_when_resolved_then_matches_unaccented_team(self, dataset):
        from brazilian_soccer.query import resolve_team
        assert resolve_team(dataset, "Grêmio") == "gremio"
        assert resolve_team(dataset, "Gremio") == "gremio"
        assert resolve_team(dataset, "São Paulo") == "sao paulo"


class TestCompetitionStructure:
    """Scenario: Competitions carry their seasons and sources
        Given the loaded dataset
        Then Serie A should span 2003-2023 across sources
        And Copa do Brasil and Libertadores should be present as cups
    """

    def test_given_dataset_when_inspecting_competitions_then_expected_competitions_exist(self, dataset):
        comps = dataset.competition_seasons()
        assert SERIE_A in comps and COPA_DO_BRASIL in comps and LIBERTADORES in comps
        assert min(s for s in comps[SERIE_A] if s) == 2003
        assert max(s for s in comps[SERIE_A] if s) == 2023
        assert 2019 in comps[LIBERTADORES]

    def test_given_2021_serie_a_when_picking_canonical_source_then_polluted_source_rejected(self, dataset):
        source, polluted = dataset.canonical_source(SERIE_A, 2021)
        assert source == SOURCE_BRASILEIRAO
        assert polluted is False

    def test_given_2023_serie_a_when_picking_canonical_source_then_br_football_used(self, dataset):
        source, _ = dataset.canonical_source(SERIE_A, 2023)
        assert source == SOURCE_BRFB

    def test_given_2005_serie_a_when_picking_canonical_source_then_historical_file_used(self, dataset):
        source, _ = dataset.canonical_source(SERIE_A, 2005)
        assert source == SOURCE_NOVO
