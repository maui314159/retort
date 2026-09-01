"""Unit tests for the normalization layer (team names, dates, numbers)."""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp.normalize import (
    canonical_competition,
    canonical_team,
    key_team,
    parse_date,
    parse_int,
    unaccent,
)


class TestTeamCanonicalization:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            # State suffix variants
            ("Palmeiras-SP", "Palmeiras"),
            ("Palmeiras - SP", "Palmeiras"),
            ("Grêmio - RS", "Grêmio"),
            ("Vasco Da Gama RJ", "Vasco da Gama"),
            ("Botafogo RJ", "Botafogo"),
            # Commentaries and country qualifiers
            (
                "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ",
                "Boavista",
            ),
            ("Nacional (URU)", "Nacional (Uruguay)"),
            ("Nacional-URU", "Nacional (Uruguay)"),
            ("Barcelona-EQU", "Barcelona (Ecuador)"),
            ("Olimpia-PAR", "Olimpia (Paraguay)"),
            # Accented vs unaccented spellings
            ("Sao Paulo", "São Paulo"),
            ("São Paulo-SP", "São Paulo"),
            ("Cuiaba", "Cuiabá"),
            ("Avai", "Avaí"),
            # Club prefixes and full legal names
            ("EC Bahia", "Bahia"),
            ("Sport Club Corinthians Paulista", "Corinthians"),
            ("Fortaleza Esporte Clube", "Fortaleza"),
            ("Fortaleza FC", "Fortaleza"),
            ("Fortaleza EC", "Fortaleza"),
            # The three Atleticos must stay distinct
            ("Atletico-PR", "Athletico Paranaense"),
            ("Athletico", "Athletico Paranaense"),
            ("Atlético - MG", "Atlético Mineiro"),
            ("Atletico Mineiro", "Atlético Mineiro"),
            ("Atletico-GO", "Atlético Goianiense"),
            ("Atletico Goianiense", "Atlético Goianiense"),
            # Ambiguous bases keep their qualifier
            ("América - MG", "América Mineiro"),
            ("América - RN", "América-RN"),
            ("Nacional - AM", "Nacional-AM"),
            ("Vitória - ES", "Vitória-ES"),
            ("Vitoria-BA", "Vitória"),
            # Names that must never be mangled
            ("LDU", "LDU"),
            ("Colo-Colo", "Colo-Colo"),
            ("The Strongest", "The Strongest"),
            ("Vitória da Conquista", "Vitória da Conquista"),
            ("Vila Nova", "Vila Nova"),
            ("Villa Nova", "Villa Nova"),
            ("", ""),
        ],
    )
    def test_canonical_team(self, raw: str, expected: str) -> None:
        assert canonical_team(raw) == expected

    def test_all_variants_share_one_key(self) -> None:
        variants = ["Palmeiras-SP", "Palmeiras", "palmeiras"]
        keys = {key_team(v) for v in variants}
        assert len(keys) == 1

    def test_atleticos_have_distinct_keys(self) -> None:
        keys = {
            key_team("Atletico-MG"),
            key_team("Atletico-PR"),
            key_team("Atletico-GO"),
        }
        assert len(keys) == 3


class TestDateParsing:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("2012-05-19 18:30:00", "2012-05-19"),
            ("2023-09-24", "2023-09-24"),
            ("29/03/2003", "2003-03-29"),
            ("19/05/2012", "2012-05-19"),
        ],
    )
    def test_known_formats(self, raw: str, expected: str) -> None:
        assert parse_date(raw) == expected

    @pytest.mark.parametrize("raw", ["NA", "", "-", None, "not a date"])
    def test_invalid_dates_return_none(self, raw) -> None:
        assert parse_date(raw) is None

    def test_brazilian_day_first(self) -> None:
        # 05/03/2003 is 5 March, not 3 May
        assert parse_date("05/03/2003") == "2003-03-05"


class TestNumberParsing:
    @pytest.mark.parametrize(
        "raw,expected",
        [("2", 2), ("2.0", 2), ("-1", -1), ("NA", None), ("-", None), ("", None), ("x", None)],
    )
    def test_parse_int(self, raw, expected) -> None:
        assert parse_int(raw) == expected


class TestCompetitions:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("Serie A", "Brasileirão Série A"),
            ("Serie B", "Brasileirão Série B"),
            ("Copa do Brasil", "Copa do Brasil"),
            ("Copa Libertadores", "Copa Libertadores"),
            ("Libertadores", "Copa Libertadores"),
        ],
    )
    def test_canonical_competition(self, raw: str, expected: str) -> None:
        assert canonical_competition(raw) == expected


def test_unaccent() -> None:
    assert unaccent("São Paulo") == "Sao Paulo"
    assert unaccent("Avaí") == "Avai"
