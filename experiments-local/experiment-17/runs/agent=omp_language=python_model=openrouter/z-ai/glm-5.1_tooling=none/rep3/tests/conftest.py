"""
Shared pytest fixtures for BDD tests.
Provides a SoccerData instance and a ToolInvoker that calls the
MCP tool functions directly (in-process, no server needed).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data_loader import SoccerData

# Re-use a single data instance across all tests
_data: SoccerData | None = None


def get_data() -> SoccerData:
    global _data
    if _data is None:
        _data = SoccerData()
    return _data


class ToolInvoker:
    """Thin wrapper that imports and calls MCP tool functions directly."""

    def __init__(self):
        from server import (
            search_matches,
            head_to_head,
            team_statistics,
            top_teams_by_goals,
            search_players,
            players_at_club,
            competition_standings,
            list_competitions,
            list_seasons,
            avg_goals_per_match,
            biggest_wins,
            home_vs_away,
        )
        self.search_matches = search_matches
        self.head_to_head = head_to_head
        self.team_statistics = team_statistics
        self.top_teams_by_goals = top_teams_by_goals
        self.search_players = search_players
        self.players_at_club = players_at_club
        self.competition_standings = competition_standings
        self.list_competitions = list_competitions
        self.list_seasons = list_seasons
        self.avg_goals_per_match = avg_goals_per_match
        self.biggest_wins = biggest_wins
        self.home_vs_away = home_vs_away


@pytest.fixture
def invoker() -> ToolInvoker:
    return ToolInvoker()


@pytest.fixture
def soccer_data() -> SoccerData:
    return get_data()
