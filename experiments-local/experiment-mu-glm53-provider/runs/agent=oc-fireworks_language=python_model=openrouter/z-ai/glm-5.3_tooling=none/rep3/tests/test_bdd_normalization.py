"""Feature: Data Quality — Normalisation, Dates, Encoding (BDD)

Spec scenarios (from "Data Quality Notes"):

    Scenario: Team name variations resolve to one identity
      Given the datasets spell clubs differently
        ("Palmeiras-SP", "Palmeiras", full names, dotted lowercase)
      When I canonicalise each spelling
      Then they all map to the same team

    Scenario: Multiple date formats parse to real dates
      Given ISO, ISO+time and Brazilian (DD/MM/YYYY) dates
      When I parse them
      Then each yields the correct calendar date

    Scenario: Missing scores are handled
      Given 'NA' and '-' goal sentinels in the raw data
      When matches are loaded
      Then those matches carry unknown (None) scores instead of crashing
"""

from __future__ import annotations

from datetime import date

import pytest

from brsoccer.dates import parse_date, parse_int, parse_season
from brsoccer.normalize import strip_accents

pytestmark = pytest.mark.bdd


class TestTeamNameVariations:
    """Scenario: Team name variations resolve to one identity."""

    CASES = [
        # (canonical key, accepted spellings)
        ("palmeiras", ["Palmeiras-SP", "Palmeiras", "PALMEIRAS", "palmeiras sp"]),
        ("flamengo rj", ["Flamengo-RJ", "Flamengo", "Flamengo - RJ"]),
        ("atletico mg", ["Atletico-MG", "Atlético-MG", "Atletico Mineiro", "Atlético Mineiro - MG", "Atlético Mineiro"]),
        ("atletico pr", ["Atletico-PR", "Atlético-PR", "Athletico-PR", "Athletico Paranaense", "Atletico Paranaense", "Athletico"]),
        ("vasco", ["Vasco da Gama-RJ", "Vasco", "Vasco Da Gama RJ", "Vasco da Gama - RJ"]),
        ("corinthians", ["Corinthians-SP", "Corinthians", "Sport Club Corinthians Paulista"]),
        ("gremio", ["Grêmio", "Gremio-RS", "Grêmio - RS", "Gremio"]),
        ("sao paulo", ["São Paulo-SP", "São Paulo", "Sao Paulo-SP", "sao paulo"]),
        ("santos sp", ["Santos-SP", "Santos", "Santos - SP"]),
        ("botafogo rj", ["Botafogo-RJ", "Botafogo", "Botafogo de Futebol e Regatas"]),
        ("sport", ["Sport-PE", "Sport Recife", "Sport Club do Recife"]),
        ("ceara", ["Ceará-CE", "Ceara-CE", "Ceará Sporting Club"]),
        ("bragantino sp", ["Red Bull Bragantino", "Red Bull Bragantino-SP", "Bragantino-SP", "Bragantino - SP"]),
        ("america mg", ["América-MG", "America-MG", "America MG", "América - MG", "América FC (Minas Gerais)"]),
        ("abc", ["A.b.c. - RN", "ABC - RN", "Abc - RN"]),
        ("bahia", ["EC Bahia", "Bahia", "Bahia - BA"]),
    ]

    @pytest.mark.parametrize(("key", "spellings"), CASES)
    def test_all_spellings_map_to_one_team(self, sd, key, spellings):
        # Given the many spellings used across the six files
        # When I canonicalise each one
        keys = {sd.registry.key_of(spelling) for spelling in spellings}
        # Then they all map to the same canonical team
        assert keys == {key}, f"spellings {spellings} produced {keys}"

    def test_ambiguous_bases_keep_their_state_suffix(self, sd):
        # Given two different clubs share a base name
        # When I canonicalise each
        # Then the state suffix keeps them apart
        assert sd.registry.key_of("Santos-SP") == "santos sp"
        assert sd.registry.key_of("Santos - AP") == "santos ap"
        assert sd.registry.key_of("Botafogo-RJ") == "botafogo rj"
        assert sd.registry.key_of("Botafogo - PB") == "botafogo pb"
        assert sd.registry.key_of("Botafogo SP") == "botafogo sp"
        assert sd.registry.key_of("América-MG") == "america mg"
        assert sd.registry.key_of("América-RN") == "america rn"
        assert sd.registry.key_of("Internacional-RS") == "internacional rs"
        assert sd.registry.key_of("EC Internacional SC") == "internacional sc"

    def test_display_names_keep_accents(self, sd):
        # Given Brazilian Portuguese names
        # When the registry picks display names
        # Then accents are preserved (UTF-8 clean output)
        assert sd.team_display("gremio") == "Grêmio"
        assert sd.team_display("sao paulo") == "São Paulo"
        assert sd.team_display("avai") == "Avaí"

    def test_resolution_ranks_prominent_teams_first(self, sd):
        # Given an ambiguous bare name like "Santos"
        # When I resolve it
        results = sd.registry.resolve("Santos")
        # Then the famous club (Santos-SP) ranks first
        assert results[0].key == "santos sp"
        assert results[0].exact is True
        # And the small Santos-AP club is still listed as an alternative
        assert any(r.key == "santos ap" for r in results)


class TestDateFormats:
    """Scenario: Multiple date formats parse to real dates."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("2012-05-19 18:30:00", date(2012, 5, 19)),
            ("2023-09-24", date(2023, 9, 24)),
            ("29/03/2003", date(2003, 3, 29)),
            ("07/02/2015 21:35:00", date(2015, 2, 7)),
            ("2019-11-23 17:00:00", date(2019, 11, 23)),
        ],
    )
    def test_parse_date_handles_all_formats(self, raw, expected):
        # Given the three date conventions in the datasets
        # When I parse each raw value
        # Then the correct calendar date comes back
        assert parse_date(raw) == expected

    def test_parse_date_rejects_sentinels(self):
        # Given missing/sentinel values
        # When I parse them
        # Then None comes back instead of an exception
        for bad in ("NA", "-", "", None, "TBD"):
            assert parse_date(bad) is None

    def test_parse_int_handles_sentinels_and_floats(self):
        # Given goal columns with 'NA', '-' and float formatting
        # When I parse them
        assert parse_int("NA") is None
        assert parse_int("-") is None
        assert parse_int("2.0") == 2
        assert parse_int("8") == 8

    def test_parse_season(self):
        assert parse_season("2019") == 2019
        assert parse_season("NA") is None
        assert parse_season("") is None


class TestMissingScores:
    """Scenario: Missing scores do not break loading."""

    def test_libertadores_dash_goals_are_none(self, sd):
        # Given Libertadores rows with '-' scores
        # When matches are loaded (and same-match duplicates merge)
        unplayed = [m for m in sd.matches_for_competition("libertadores") if not m.played]
        # Then two matches carry unknown scores, flagged as unplayed
        assert len(unplayed) == 2
        assert all(m.home_goal is None and m.away_goal is None for m in unplayed)
        # And one of them is the famous abandoned Boca Juniors vs River
        # Plate last-16 first leg (2015-05-14), correctly scoreless
        boca_river = next(m for m in unplayed if m.season == 2015)
        assert {boca_river.home_display, boca_river.away_display} == {"Boca Juniors", "River Plate"}
        assert boca_river.date.isoformat() == "2015-05-14"

    def test_unplayed_matches_are_excluded_from_standings(self, sd):
        # Given unplayed matches exist
        # When standings are computed
        from brsoccer import queries as q

        table = q.standings(sd, "serie_a", 2019)
        # Then only scored matches count (38 per team)
        assert all(row.played == 38 for row in table)


class TestEncoding:
    """Scenario: UTF-8 handling for Brazilian Portuguese."""

    def test_accents_stripped_for_matching_but_kept_for_display(self):
        # Given accented text
        # When normalised for matching
        assert strip_accents("São Paulo Grêmio Avaí Fortaleza") == "Sao Paulo Gremio Avai Fortaleza"

    def test_match_rows_render_utf8_scores(self, sd):
        # Given matches involving accented club names
        # When I format them
        from brsoccer.formatting import format_match

        sample = next(
            m
            for m in sd.matches_for_competition("serie_a")
            if "Grêmio" in (m.home_display, m.away_display) and m.played and m.stage
        )
        line = format_match(sample)
        # Then the accented display name survives (UTF-8 clean)
        assert "Grêmio" in line
        assert "Round" in line
