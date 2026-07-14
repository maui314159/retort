"""
test_data_loader.py
====================

Unit tests for the CSV ingestion and team-name normalization layer.
"""

from __future__ import annotations

import pandas as pd
import pytest

import data_loader


@pytest.fixture(autouse=True)
def _reset_loader_cache() -> None:
    data_loader.clear_cache()
    yield
    data_loader.clear_cache()


# ---------------------------------------------------------------------------
# normalize_team_name
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Palmeiras-SP", "palmeiras"),
        ("Flamengo-RJ", "flamengo"),
        ("São Paulo", "sao paulo"),
        ("Sao Paulo-SP", "sao paulo"),
        ("Grêmio", "gremio"),
        ("Atletico-MG", "atletico mineiro"),
        ("Atlético-MG", "atletico mineiro"),
        ("Athletico Paranaense", "athletico paranaense"),
        ("Athletico-PR", "athletico paranaense"),
        ("Atletico-PR", "athletico paranaense"),
        ("Botafogo RJ", "botafogo"),
        ("Vasco da Gama-RJ", "vasco"),
        ("Nacional (URU)", "nacional"),
        ("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", "boavista sport club"),
        ("SãoPaulo", "saopaulo"),
        ("Csa-AL", "csa"),
        ("Fortaleza-CE", "fortaleza"),
    ],
)
def test_normalize_team_name(raw: str, expected: str) -> None:
    assert data_loader.normalize_team_name(raw) == expected


def test_normalize_team_name_handles_non_string() -> None:
    assert data_loader.normalize_team_name(None) == ""
    assert data_loader.normalize_team_name(123) == ""


# ---------------------------------------------------------------------------
# _parse_date
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,year,month,day",
    [
        ("2023-09-24", 2023, 9, 24),
        ("2023-09-24 18:30:00", 2023, 9, 24),
        ("29/03/2003", 2003, 3, 29),
        ("19/05/2019", 2019, 5, 19),
    ],
)
def test_parse_date_formats(raw: str, year: int, month: int, day: int) -> None:
    parsed = data_loader._parse_date(raw)
    assert parsed is not pd.NaT
    assert parsed.year == year
    assert parsed.month == month
    assert parsed.day == day


def test_parse_date_empty_returns_nat() -> None:
    assert data_loader._parse_date("") is pd.NaT
    assert data_loader._parse_date(None) is pd.NaT


# ---------------------------------------------------------------------------
# load_matches
# ---------------------------------------------------------------------------


def test_load_matches_returns_all_competitions() -> None:
    df = data_loader.load_matches()
    assert not df.empty
    competitions = set(df["competition"].unique())
    assert "Brasileirão" in competitions
    assert "Copa do Brasil" in competitions
    assert "Copa Libertadores" in competitions


def test_load_matches_has_canonical_columns() -> None:
    df = data_loader.load_matches()
    expected = {
        "match_id",
        "competition",
        "season",
        "round",
        "stage",
        "date",
        "home_team_display",
        "away_team_display",
        "home_team_key",
        "away_team_key",
        "home_goal",
        "away_goal",
    }
    assert expected.issubset(df.columns)


def test_load_matches_no_duplicate_within_season() -> None:
    """A given pair should not play each other twice in the same round/date."""
    df = data_loader.load_matches()
    df_sorted = df.dropna(subset=["date"])
    df_sorted["_date_only"] = df_sorted["date"].dt.normalize()
    df_sorted["_pair"] = (
        df_sorted[["home_team_key", "away_team_key"]].min(axis=1)
        + "::"
        + df_sorted[["home_team_key", "away_team_key"]].max(axis=1)
    )
    duplicates = df_sorted.groupby(
        ["competition", "season", "_date_only", "_pair"]
    ).size()
    assert (duplicates <= 1).all(), (
        f"Found duplicate matches: {duplicates[duplicates > 1]}"
    )


# ---------------------------------------------------------------------------
# load_players
# ---------------------------------------------------------------------------


def test_load_players_has_brazilian_players() -> None:
    df = data_loader.load_players()
    assert not df.empty
    brazilian = df[df["nationality"] == "Brazil"]
    assert len(brazilian) > 100


def test_load_players_has_derived_keys() -> None:
    df = data_loader.load_players()
    assert "name_key" in df.columns
    assert "club_key" in df.columns
    assert "nationality_key" in df.columns


# ---------------------------------------------------------------------------
# resolve_competition
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "query,expected",
    [
        ("Brasileirão", ["Brasileirão"]),
        ("brasileirao", ["Brasileirão"]),
        ("Serie A", ["Brasileirão"]),
        ("Copa do Brasil", ["Copa do Brasil"]),
        ("Libertadores", ["Copa Libertadores"]),
    ],
)
def test_resolve_competition(query: str, expected: list[str]) -> None:
    assert data_loader.resolve_competition(query) == expected


def test_resolve_competition_unknown() -> None:
    assert data_loader.resolve_competition("XYZ League") is None


# ---------------------------------------------------------------------------
# resolve_team_name
# ---------------------------------------------------------------------------


def test_resolve_team_name_with_state_suffix() -> None:
    df = data_loader.load_matches()
    # "Palmeiras-SP" should resolve to the same key as "Palmeiras".
    assert data_loader.resolve_team_name("Palmeiras-SP", df) == "palmeiras"


def test_resolve_team_name_handles_accents() -> None:
    df = data_loader.load_matches()
    # "São Paulo" (accented) and "Sao Paulo" should map to the same key.
    key1 = data_loader.resolve_team_name("São Paulo", df)
    key2 = data_loader.resolve_team_name("Sao Paulo", df)
    assert key1 == key2
    assert key1 is not None
    assert key1 == "sao paulo"
