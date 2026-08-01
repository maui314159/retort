"""Unit tests for team/competition/date normalization."""

from __future__ import annotations

from datetime import datetime

import pytest

from soccer_mcp.normalize import (
    canonical_competition,
    canonical_team,
    derby_name,
    normalize_text,
    parse_date,
    parse_user_date,
)


class TestTeamNames:
    """State-suffixed, accented and full-name variations must converge."""

    @pytest.mark.parametrize("raw,expected", [
        ("Palmeiras-SP", "palmeiras"),
        ("Flamengo-RJ", "flamengo"),
        ("São Paulo", "sao paulo"),
        ("São Paulo-SP", "sao paulo"),
        ("Sao Paulo", "sao paulo"),
        ("Grêmio", "gremio"),
        ("Grêmio-RS", "gremio"),
        ("Athletico-PR", "athletico paranaense"),
        ("Atlético-PR", "athletico paranaense"),
        ("Athletico Paranaense", "athletico paranaense"),
        ("Atletico Paranaense", "athletico paranaense"),
        ("Atlético-MG", "atletico mineiro"),
        ("Atletico Mineiro", "atletico mineiro"),
        ("Atlético-GO", "atletico goianiense"),
        ("América - MG", "america mineiro"),
        ("America MG", "america mineiro"),
        ("Sport-PE", "sport recife"),
        ("Sport Recife", "sport recife"),
        ("Botafogo-RJ", "botafogo"),
        ("Botafogo RJ", "botafogo"),
        ("Vasco-RJ", "vasco"),
        ("Vasco Da Gama RJ", "vasco"),
        ("Vasco da Gama", "vasco"),
        ("EC Bahia", "bahia"),
        ("Bahia-BA", "bahia"),
        ("EC Vitória", "vitoria"),
        ("Fortaleza-CE", "fortaleza"),
        ("Fortaleza FC", "fortaleza"),
        ("Fluminense-RJ", "fluminense"),
        ("Corinthians-SP", "corinthians"),
        ("Sport Club Corinthians Paulista", "corinthians"),
        ("Coritiba-PR", "coritiba"),
        ("Cuiaba-MT", "cuiaba"),
        ("Cuiaba MT", "cuiaba"),
        ("Red Bull Bragantino", "bragantino"),
        ("Avaí-SC", "avai"),
        ("Ceará-CE", "ceara"),
        ("Goiás-GO", "goias"),
        ("Barcelona-EQU", "barcelona sc"),
        ("Boca Juniors", "boca juniors"),
        ("River Plate", "river plate"),
        ("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", "boavista"),
        ("4 de Julho EC", "4 de julho"),
        ("4 de Julho - PI", "4 de julho"),
    ])
    def test_canonical_team(self, raw, expected):
        assert canonical_team(raw) == expected

    @pytest.mark.parametrize("raw,expected", [
        # Distinct clubs that merely share a short name must NOT merge.
        ("Botafogo-PB", "botafogo pb"),
        ("Botafogo-SP", "botafogo sp"),
        ("Rio Branco - AC", "rio branco ac"),
        ("Rio Branco - ES", "rio branco es"),
        ("Fluminense-PI", "fluminense pi"),
        ("Operário-MS", "operario ms"),
        ("Operário-PR", "operario pr"),
        ("Nacional - AM", "nacional am"),
    ])
    def test_distinct_clubs_do_not_merge(self, raw, expected):
        assert canonical_team(raw) == expected

    def test_cross_source_forms_agree(self):
        """The same club named differently per file must dedupe together."""
        assert canonical_team("Atlético - BA") == canonical_team("Atletico Alagoinhas")
        assert canonical_team("Afogados - PE") == canonical_team("Afogados da Ingazeira FC")
        assert canonical_team("Moto Club - MA") == canonical_team("Moto Club de Sao Luis")

    def test_empty_and_none(self):
        assert canonical_team(None) == ""
        assert canonical_team("") == ""


class TestNormalizeText:
    def test_accents_and_case(self):
        assert normalize_text("São Paulo") == "sao paulo"
        assert normalize_text("Grêmio") == "gremio"
        assert normalize_text("Avaí") == "avai"
        assert normalize_text("Fortaleza Esporte Clube") == "fortaleza esporte clube"

    def test_whitespace_and_parentheticals(self):
        assert normalize_text("Nacional (URU)") == "nacional"
        assert normalize_text("  Santos   FC ") == "santos fc"


class TestCompetitions:
    @pytest.mark.parametrize("raw,expected", [
        ("Brasileirão", "serie a"),
        ("brasileirao", "serie a"),
        ("Serie A", "serie a"),
        ("Brasileirão Série A", "serie a"),
        ("Campeonato Brasileiro", "serie a"),
        ("Serie B", "serie b"),
        ("Serie C", "serie c"),
        ("Copa do Brasil", "copa do brasil"),
        ("copa do brasil", "copa do brasil"),
        ("Libertadores", "copa libertadores"),
        ("Copa Libertadores", "copa libertadores"),
        ("CONMEBOL Libertadores", "copa libertadores"),
        ("Copa do Brasil 2023", "copa do brasil"),
    ])
    def test_canonical_competition(self, raw, expected):
        assert canonical_competition(raw) == expected

    def test_unknown(self):
        assert canonical_competition("Champions League") is None
        assert canonical_competition("") is None
        assert canonical_competition(None) is None


class TestDates:
    def test_iso(self):
        assert parse_date("2023-09-24") == datetime(2023, 9, 24)

    def test_iso_with_time(self):
        assert parse_date("2012-05-19 18:30:00") == datetime(2012, 5, 19, 18, 30)

    def test_brazilian_format(self):
        assert parse_date("29/03/2003") == datetime(2003, 3, 29)

    def test_invalid_and_empty(self):
        assert parse_date("") is None
        assert parse_date(None) is None
        assert parse_date("not a date") is None
        assert parse_date("nan") is None

    def test_user_dates(self):
        assert parse_user_date("2019") == datetime(2019, 1, 1)
        assert parse_user_date("2019-04-27") == datetime(2019, 4, 27)
        assert parse_user_date("27/04/2019") == datetime(2019, 4, 27)
        assert parse_user_date(None) is None


class TestDerbies:
    def test_known_derbies(self):
        assert derby_name("flamengo", "fluminense") == "Fla-Flu"
        assert derby_name("gremio", "internacional") == "Gre-Nal"
        assert derby_name("corinthians", "palmeiras") == "Derby Paulista"
        assert derby_name("bahia", "vitoria") == "Ba-Vi"

    def test_order_irrelevant(self):
        assert derby_name("fluminense", "flamengo") == "Fla-Flu"

    def test_non_derby(self):
        assert derby_name("flamengo", "palmeiras") is None
