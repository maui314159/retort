"""Shared pytest fixtures for the Brazilian Soccer MCP test-suite.

Context block
-------------
Provides a session-scoped ``DataLoader`` fixture (loading the real Kaggle
CSVs once) and a ``server`` fixture that wires the query layer into a
``FastMCP`` instance for tool-level tests.
"""
from __future__ import annotations

import pytest

from brazilian_soccer_mcp.data_loader import DataLoader
from brazilian_soccer_mcp.queries import (
    average_goals,
    biggest_wins,
    compare_teams,
    competition_seasons,
    competition_standings,
    find_head_to_head,
    find_matches,
    home_vs_away_record,
    last_match_between,
    list_competitions,
    search_players,
    team_statistics,
    top_players_at_club,
)
from brazilian_soccer_mcp.server import create_server


@pytest.fixture(scope="session")
def loader() -> DataLoader:
    return DataLoader()


@pytest.fixture(scope="session")
def server(loader: DataLoader):
    return create_server(loader)


# Expose query functions as a convenient fixture for BDD step modules.
@pytest.fixture(scope="session")
def queries():
    return {
        "find_matches": find_matches,
        "find_head_to_head": find_head_to_head,
        "team_statistics": team_statistics,
        "compare_teams": compare_teams,
        "search_players": search_players,
        "top_players_at_club": top_players_at_club,
        "competition_standings": competition_standings,
        "competition_seasons": competition_seasons,
        "average_goals": average_goals,
        "biggest_wins": biggest_wins,
        "home_vs_away_record": home_vs_away_record,
        "last_match_between": last_match_between,
        "list_competitions": list_competitions,
    }
