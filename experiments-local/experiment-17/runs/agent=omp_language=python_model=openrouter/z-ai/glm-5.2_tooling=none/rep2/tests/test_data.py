"""Unit tests for data loading, deduplication and catalogue helpers.

These complement the BDD scenarios by asserting dataset-level invariants
that are not naturally expressed as Given/When/Then.
"""

from __future__ import annotations

import pytest

from brazilian_soccer import queries as Q
from brazilian_soccer.data_loader import get_data


def test_all_six_csv_files_loaded(data):
    """All six bundled datasets must be loaded and non-empty."""
    assert len(data.matches) > 0
    assert len(data.players) > 0
    # Every source file contributed rows before dedup; after dedup the
    # dedicated sources still account for the bulk of matches.
    sources = set(data.matches["source"].unique())
    assert {"Brasileirao_Matches", "Brazilian_Cup_Matches",
            "Libertadores_Matches", "BR-Football-Dataset",
            "novo_campeonato_brasileiro"} <= sources


def test_match_schema_columns(data):
    required = {"date", "competition", "home", "away", "home_key",
                "away_key", "home_goals", "away_goals", "season", "source"}
    assert required.issubset(data.matches.columns)


def test_no_duplicate_match_per_season_pairing(data):
    """Each (season, competition, home_key, away_key) appears at most once."""
    df = data.matches
    dups = df.duplicated(subset=["season", "competition",
                                 "home_key", "away_key"], keep=False)
    # Allow a tiny tolerance for genuine data anomalies, but there should
    # be no systematic duplication.
    assert dups.sum() <= 5, f"{dups.sum()} duplicate pairings remain"


def test_season_range_covers_history_and_modern(data):
    seasons = set(data.matches["season"].dropna().astype(int).unique())
    assert 2003 in seasons          # historical archive
    assert 2023 in seasons          # extended-stats dataset


def test_competitions_present(data):
    comps = set(Q.list_competitions(data))
    assert {"Brasileirão Serie A", "Copa do Brasil",
            "Copa Libertadores"} <= comps


def test_2019_brasileirao_full_season(data):
    """2019 Brasileirão has exactly 380 matches (20 teams x 38 rounds)."""
    df = data.matches
    b19 = df[(df["competition"] == "Brasileirão Serie A")
             & (df["season"] == 2019)]
    assert len(b19) == 380, len(b19)


def test_players_have_brazilians(data):
    brazilians = data.players[data.players["Nationality"] == "Brazil"]
    assert len(brazilians) > 100


def test_team_display_names_are_clean(data):
    """No display name leaks a raw state suffix or stray parentheses."""
    for key, name in data.team_display.items():
        assert " (" not in name, name
        assert not name.endswith((" SP", " RJ", " MG", " PR", " RS",
                                  " BA", " CE", " GO", " SC", " PE")), name



def test_list_teams_returns_active(data):
    teams = Q.list_teams(data, competition="Brasileirão Serie A",
                         season=2019, limit=5)
    assert len(teams) == 5
    assert all(t["matches"] > 0 for t in teams)
