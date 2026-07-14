"""
================================================================================
Context
--------------------------------------------------------------------------------
Module  : tests.test_normalize
Purpose : Unit tests for brazilian_soccer.normalize - the team-name / date /
          score parsing that underpins all matching. These guard the data-
          quality rules called out in the spec (suffixes, accents, mixed date
          and score formats) and the state-aware key design.
================================================================================
"""

from __future__ import annotations

from datetime import date

import pytest

from brazilian_soccer.normalize import (
    base_of,
    display_team,
    normalize_team,
    parse_date,
    parse_score,
    split_team,
    team_key,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Palmeiras-SP", "palmeiras"),
        ("Palmeiras - SP", "palmeiras"),
        ("Grêmio", "gremio"),
        ("Avaí", "avai"),
        ("Nacional (URU)", "nacional"),
        ("Sport Club Corinthians Paulista", "corinthians"),
        ("  São  Paulo  ", "sao paulo"),
        ("Athletico-PR", "atletico"),
        ("Vasco da Gama", "vasco"),
        (None, ""),
        ("nan", ""),
    ],
)
def test_normalize_team_base(raw, expected):
    assert normalize_team(raw) == expected


def test_team_key_from_suffix():
    # State comes from the name suffix; bare names get a base-only key.
    assert team_key("Flamengo-RJ") == "flamengo|rj"
    assert team_key("Flamengo") == "flamengo"


def test_team_key_distinguishes_same_base_clubs():
    assert team_key("Atletico-MG") == "atletico|mg"
    assert team_key("Atletico-PR") == "atletico|pr"


def test_distinct_clubs_have_distinct_keys():
    assert team_key("Atletico-MG") != team_key("Atletico-PR")
    assert base_of(team_key("Atletico-MG")) == base_of(team_key("Atletico-PR"))


def test_split_team_returns_state():
    assert split_team("América - MG") == ("america", "mg")
    assert split_team("Santos") == ("santos", None)


def test_display_team_keeps_accents_drops_suffix():
    assert display_team("Grêmio-RS") == "Grêmio"
    assert display_team("Nacional (URU)") == "Nacional"


@pytest.mark.parametrize(
    "raw,expected",
    [
        (2, 2),
        (1.0, 1),
        ("2", 2),
        ("1.0", 1),
        ("-", None),
        ("", None),
        (None, None),
        (float("nan"), None),
    ],
)
def test_parse_score(raw, expected):
    assert parse_score(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("2023-09-24", date(2023, 9, 24)),
        ("2012-05-19 18:30:00", date(2012, 5, 19)),
        ("29/03/2003", date(2003, 3, 29)),
        ("garbage", None),
        ("", None),
        (None, None),
    ],
)
def test_parse_date(raw, expected):
    assert parse_date(raw) == expected
