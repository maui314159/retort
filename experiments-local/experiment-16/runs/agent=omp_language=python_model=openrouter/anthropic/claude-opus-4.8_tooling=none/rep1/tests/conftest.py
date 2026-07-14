"""
================================================================================
Context
--------------------------------------------------------------------------------
Module  : tests.conftest
Purpose : Shared pytest fixtures for the Brazilian Soccer MCP test suite.

Two graphs are offered:
  * ``sample_graph`` - a tiny, fully-controlled synthetic dataset written to a
    temp dir, used by the BDD behavior scenarios so assertions are exact and the
    tests stay fast and offline.
  * ``real_graph``   - the full graph loaded from data/kaggle/, session-scoped
    and used only by the integration checks that assert against known real
    results (e.g. the 2019 Brasileirão title race).
================================================================================
"""

from __future__ import annotations

import os

import pytest

from brazilian_soccer import SoccerGraph, load_graph
from brazilian_soccer.loader import load_matches, load_players

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_REPO, "data", "kaggle")


def _write_sample(data_dir: str) -> None:
    """Write a minimal but representative set of CSVs into *data_dir*."""
    os.makedirs(data_dir, exist_ok=True)

    # Brasileirão: a 2023 mini-league with state suffixes + a NaN-score row.
    with open(os.path.join(data_dir, "Brasileirao_Matches.csv"), "w", encoding="utf-8") as f:
        f.write(
            '"datetime","home_team","home_team_state","away_team",'
            '"away_team_state","home_goal","away_goal","season","round"\n'
        )
        rows = [
            ("2023-09-03 16:00:00", "Flamengo-RJ", "RJ", "Fluminense-RJ", "RJ", 2, 1, 2023, 22),
            ("2023-05-28 11:00:00", "Fluminense-RJ", "RJ", "Flamengo-RJ", "RJ", 1, 0, 2023, 8),
            ("2023-07-10 20:00:00", "Palmeiras-SP", "SP", "Santos-SP", "SP", 3, 0, 2023, 15),
            ("2023-08-12 18:30:00", "Santos-SP", "SP", "Palmeiras-SP", "SP", 1, 1, 2023, 18),
            ("2023-10-01 16:00:00", "Flamengo-RJ", "RJ", "Palmeiras-SP", "SP", 0, 2, 2023, 25),
            # Distinct same-base clubs must NOT merge.
            ("2023-06-01 16:00:00", "Atletico-MG", "MG", "Flamengo-RJ", "RJ", 2, 2, 2023, 10),
            ("2023-06-08 16:00:00", "Atletico-PR", "PR", "Flamengo-RJ", "RJ", 0, 1, 2023, 11),
            # Missing score row (postponed) - kept for listing, excluded from stats.
            ("2023-11-01 16:00:00", "Flamengo-RJ", "RJ", "Santos-SP", "SP", "", "", 2023, 30),
        ]
        for r in rows:
            f.write(",".join(str(x) for x in r) + "\n")

    # Copa do Brasil: name carries the state suffix, no state column.
    with open(os.path.join(data_dir, "Brazilian_Cup_Matches.csv"), "w", encoding="utf-8") as f:
        f.write('"round","datetime","home_team","away_team","home_goal","away_goal","season"\n')
        f.write('"final",2023-09-24 20:00:00,"Flamengo - RJ","Sao Paulo - SP",1,1,2023\n')

    # Libertadores: country suffix + a "-" missing score.
    with open(os.path.join(data_dir, "Libertadores_Matches.csv"), "w", encoding="utf-8") as f:
        f.write('"datetime","home_team","away_team","home_goal","away_goal","season","stage"\n')
        f.write('2023-02-12 20:15:00,"Palmeiras","Nacional (URU)","4","0",2023,"group stage"\n')
        f.write('2023-03-01 20:15:00,"Boca Juniors","Palmeiras","-","-",2023,"final"\n')

    # FIFA players: Brazilians at Brazilian and foreign clubs + one non-Brazilian.
    with open(os.path.join(data_dir, "fifa_data.csv"), "w", encoding="utf-8") as f:
        f.write(
            ",ID,Name,Age,Photo,Nationality,Flag,Overall,Potential,Club,Club Logo,"
            "Value,Wage,Special,Preferred Foot,International Reputation,Weak Foot,"
            "Skill Moves,Work Rate,Body Type,Real Face,Position,Jersey Number,Joined,"
            "Loaned From,Contract Valid Until,Height,Weight\n"
        )
        players = [
            (0, 1, "Neymar Jr", 31, "Brazil", 89, 89, "Paris Saint-Germain", "LW"),
            (1, 2, "Gabriel Barbosa", 27, "Brazil", 82, 83, "Flamengo", "ST"),
            (2, 3, "Pedro", 26, "Brazil", 80, 82, "Flamengo", "ST"),
            (3, 4, "Endrick", 17, "Brazil", 70, 88, "Palmeiras", "ST"),
            (4, 5, "Lionel Messi", 36, "Argentina", 90, 90, "Inter Miami", "RW"),
        ]
        for idx, pid, name, age, nat, ov, pot, club, pos in players:
            f.write(
                f"{idx},{pid},{name},{age},,{nat},,{ov},{pot},{club},,"
                f"€1M,€1K,0,Right,3,3,3,Medium/ Medium,Normal,Yes,{pos},10,"
                '"Jul 1, 2020",,2025,5\'9,160lbs\n'
            )


@pytest.fixture(scope="session")
def sample_data_dir(tmp_path_factory) -> str:
    d = tmp_path_factory.mktemp("kaggle_sample")
    _write_sample(str(d))
    return str(d)


@pytest.fixture(scope="session")
def sample_graph(sample_data_dir) -> SoccerGraph:
    return SoccerGraph(load_matches(sample_data_dir), load_players(sample_data_dir))


def _real_data_available() -> bool:
    return os.path.exists(os.path.join(_DATA, "Brasileirao_Matches.csv"))


@pytest.fixture(scope="session")
def real_graph() -> SoccerGraph:
    if not _real_data_available():
        pytest.skip("real Kaggle datasets not present in data/kaggle/")
    return load_graph(_DATA)


# Mutable holder so BDD step functions can pass state between Given/When/Then.
@pytest.fixture
def ctx() -> dict:
    return {}
