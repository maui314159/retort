"""Shared fixtures for the BDD test suite.

The store is session-scoped: loading the six CSVs takes ~1.5s, so all
scenarios share one SoccerStore instance.
"""

from __future__ import annotations

import pytest

from brasil_mcp import queries
from brasil_mcp.store import SoccerStore, default_data_dir


@pytest.fixture(scope="session")
def store() -> SoccerStore:
    return SoccerStore(default_data_dir())


@pytest.fixture(scope="session")
def loaded_store(store) -> SoccerStore:
    """Alias used by Gherkin 'Given the match data is loaded' steps."""
    return store


TOOL_ROUTER = {
    "find_team": queries.find_team,
    "search_matches": queries.search_matches,
    "head_to_head": queries.head_to_head,
    "team_stats": queries.team_stats,
    "team_season_history": queries.team_season_history,
    "standings": queries.standings,
    "search_players": queries.search_players,
    "team_players": queries.team_players,
    "competition_info": queries.competition_info,
    "derbies": queries.derbies,
    "biggest_wins": queries.biggest_wins,
    "goals_analysis": queries.goals_analysis,
    "best_records": queries.best_records,
    "compare_teams": queries.compare_teams,
}


@pytest.fixture(scope="session")
def ask():
    """Dispatch a natural-language-backed tool call by tool name."""

    def _ask(tool: str, **kwargs) -> dict:
        return TOOL_ROUTER[tool](**kwargs)

    return _ask
