"""
================================================================================
tests.test_normalize
================================================================================
Context:
    Focused unit tests for brazil_soccer_mcp.normalize - the most breakable
    logic in the system (team-name parsing, accent folding, multi-format date
    parsing, competition aliasing). These assert behavioral invariants, not
    incidental values.
================================================================================
"""

import datetime

import pytest

from brazil_soccer_mcp.normalize import (
    normalize_competition,
    normalize_date,
    normalize_team,
    parse_team,
)


@pytest.mark.parametrize(
    "raw, base, state",
    [
        ("Palmeiras-SP", "palmeiras", "SP"),
        ("Palmeiras", "palmeiras", None),
        ("Atlético-MG", "atletico", "MG"),
        ("São Paulo", "sao paulo", None),
        ("Sao Paulo", "sao paulo", None),
        ("Nacional (URU)", "nacional", "URU"),
        ("Barcelona-EQU", "barcelona", "EQU"),
        ("América - MG", "america", "MG"),
    ],
)
def test_parse_team_base_and_state(raw, base, state):
    assert parse_team(raw) == (base, state)


def test_parse_team_strips_parenthetical_aside():
    base, state = parse_team(
        "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"
    )
    assert base == "boavista sport club"
    assert state == "RJ"


def test_accent_folding_merges_variants():
    # Suffix and accent variants of the same club share a base key.
    assert normalize_team("Grêmio") == normalize_team("Gremio")
    assert normalize_team("São Paulo") == normalize_team("Sao Paulo")
    assert normalize_team("Palmeiras-SP") == normalize_team("Palmeiras")


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("2019-10-27", datetime.date(2019, 10, 27)),
        ("2012-05-19 18:30:00", datetime.date(2012, 5, 19)),
        ("29/03/2003", datetime.date(2003, 3, 29)),
        ("2023-09-24", datetime.date(2023, 9, 24)),
    ],
)
def test_normalize_date_formats(raw, expected):
    assert normalize_date(raw) == expected


def test_normalize_date_brazilian_is_day_first():
    # 03/04/2003 must be 3 April, not 4 March.
    assert normalize_date("03/04/2003") == datetime.date(2003, 4, 3)


def test_normalize_date_invalid_returns_none():
    assert normalize_date("not-a-date") is None
    assert normalize_date("") is None
    assert normalize_date(None) is None


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Serie A", "Brasileirao Serie A"),
        ("Brasileirão", "Brasileirao Serie A"),
        ("Copa do Brasil", "Copa do Brasil"),
        ("Libertadores", "Copa Libertadores"),
        ("Serie B", "Serie B"),
    ],
)
def test_normalize_competition(raw, expected):
    assert normalize_competition(raw) == expected
