"""
Brazilian Soccer MCP Server - MCP Server Entry Point
=====================================================
FastMCP server exposing Brazilian soccer data as MCP tools.
Uses the Model Context Protocol (MCP) to provide a knowledge graph
interface for querying Brazilian soccer matches, players, teams,
competitions, and statistics.

Data sources (6 CSV files from data/kaggle/):
  - Brasileirao_Matches.csv: Serie A matches (2012+)
  - Brazilian_Cup_Matches.csv: Copa do Brasil matches (2012+)
  - Libertadores_Matches.csv: Copa Libertadores matches (2013+)
  - BR-Football-Dataset.csv: Extended match statistics
  - novo_campeonato_brasileiro.csv: Historical Brasileirao (2003-2019)
  - fifa_data.csv: FIFA player database (18,207 players)

Usage:
    python server.py
    # Or via uv: uv run server.py
    # Or via mcp: mcp run server.py
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import pandas as pd
from mcp.server.fastmcp import FastMCP

from data_loader import (
    get_all_team_names,
    load_all_match_data,
    load_fifa_players,
)
from query_engine import (
    get_average_goals,
    get_biggest_wins,
    get_data_summary,
    get_head_to_head,
    get_highest_scoring_teams,
    get_players_by_club,
    get_season_summary,
    get_standings,
    get_team_performance_trend,
    get_team_stats,
    get_top_brazilian_players,
    search_matches,
    search_players,
)

# Logger to stderr to avoid corrupting MCP stdio transport
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("brazilian-soccer-mcp")

# Initialize FastMCP server
mcp = FastMCP("Brazilian Soccer MCP")

# ── Global data cache (loaded lazily) ───────────────────────────────────────

_matches_df: pd.DataFrame | None = None
_players_df: pd.DataFrame | None = None


def _get_matches() -> pd.DataFrame:
    global _matches_df
    if _matches_df is None:
        logger.info("Loading match data...")
        _matches_df = load_all_match_data()
        logger.info("Match data loaded: %d matches", len(_matches_df))
    return _matches_df


def _get_players() -> pd.DataFrame:
    global _players_df
    if _players_df is None:
        logger.info("Loading player data...")
        _players_df = load_fifa_players()
        logger.info("Player data loaded: %d players", len(_players_df))
    return _players_df


# ── MCP Tools ───────────────────────────────────────────────────────────────


@mcp.tool()
def tool_search_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 50,
) -> str:
    """Search Brazilian soccer matches by team, opponent, competition, season, and date range.

    Args:
        team: Team name to search for (e.g., "Flamengo", "Palmeiras")
        opponent: Opponent team name to filter by
        competition: Competition name (e.g., "Brasileirão", "Copa do Brasil", "Libertadores")
        season: Season year (e.g., 2023)
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        limit: Maximum number of results to return (default 50)
    """
    return search_matches(
        _get_matches(),
        team=team,
        opponent=opponent,
        competition=competition,
        season=season,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )


@mcp.tool()
def tool_get_team_stats(
    team: str,
    season: int | None = None,
    competition: str | None = None,
) -> str:
    """Get comprehensive statistics for a team including wins, losses, draws, goals, and home/away records.

    Args:
        team: Team name (e.g., "Flamengo", "Corinthians", "Palmeiras")
        season: Optional season year to filter by
        competition: Optional competition name to filter by
    """
    return get_team_stats(_get_matches(), team, season=season, competition=competition)


@mcp.tool()
def tool_search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    max_overall: int | None = None,
    limit: int = 20,
) -> str:
    """Search FIFA player database by name, nationality, club, position, and rating.

    Args:
        name: Player name to search for (partial match, e.g., "Neymar", "Gabriel")
        nationality: Nationality to filter by (e.g., "Brazil", "Argentina")
        club: Club name to filter by (e.g., "Flamengo", "Real Madrid")
        position: Position to filter by (e.g., "ST", "GK", "LW", "CDM")
        min_overall: Minimum overall rating (0-100)
        max_overall: Maximum overall rating (0-100)
        limit: Maximum number of results (default 20)
    """
    return search_players(
        _get_players(),
        name=name,
        nationality=nationality,
        club=club,
        position=position,
        min_overall=min_overall,
        max_overall=max_overall,
        limit=limit,
    )


@mcp.tool()
def tool_get_head_to_head(team1: str, team2: str) -> str:
    """Compare two teams head-to-head with match history and statistics.

    Args:
        team1: First team name (e.g., "Flamengo")
        team2: Second team name (e.g., "Fluminense")
    """
    return get_head_to_head(_get_matches(), team1, team2)


@mcp.tool()
def tool_get_standings(
    competition: str = "Brasileirão",
    season: int | None = None,
) -> str:
    """Calculate league standings from match results using 3-1-0 points system.

    Args:
        competition: Competition name (default "Brasileirão")
        season: Season year, or omit for all seasons combined
    """
    return get_standings(_get_matches(), competition, season)


@mcp.tool()
def tool_get_season_summary(
    competition: str = "Brasileirão",
    season: int | None = None,
) -> str:
    """Get a summary of a competition season including champion, statistics, and top standings.

    Args:
        competition: Competition name (default "Brasileirão")
        season: Season year, or omit for all-time summary
    """
    return get_season_summary(_get_matches(), competition, season)


@mcp.tool()
def tool_get_average_goals(
    competition: str | None = None,
    season: int | None = None,
) -> str:
    """Calculate average goals per match, home/away win rates, and match statistics.

    Args:
        competition: Optional competition name to filter by
        season: Optional season year to filter by
    """
    return get_average_goals(_get_matches(), competition, season)


@mcp.tool()
def tool_get_biggest_wins(
    competition: str | None = None,
    limit: int = 20,
) -> str:
    """Get the biggest victories in the dataset by goal difference.

    Args:
        competition: Optional competition name to filter by
        limit: Maximum number of results (default 20)
    """
    return get_biggest_wins(_get_matches(), competition, limit)


@mcp.tool()
def tool_get_top_brazilian_players(limit: int = 20) -> str:
    """Get the highest-rated Brazilian players in the FIFA database.

    Args:
        limit: Maximum number of results (default 20)
    """
    return get_top_brazilian_players(_get_players(), limit)


@mcp.tool()
def tool_get_players_by_club(club: str, limit: int = 30) -> str:
    """Get players for a specific club, sorted by overall rating.

    Args:
        club: Club name (e.g., "Flamengo", "Palmeiras", "São Paulo")
        limit: Maximum number of results (default 30)
    """
    return get_players_by_club(_get_players(), club, limit)


@mcp.tool()
def tool_get_highest_scoring_teams(
    competition: str | None = None,
    season: int | None = None,
    top_n: int = 10,
) -> str:
    """Find teams with the most goals scored.

    Args:
        competition: Optional competition name to filter by
        season: Optional season year to filter by
        top_n: Number of teams to return (default 10)
    """
    return get_highest_scoring_teams(_get_matches(), competition, season, top_n)


@mcp.tool()
def tool_get_team_performance_trend(
    team: str,
    competition: str = "Brasileirão",
) -> str:
    """Show a team's performance by season in a competition.

    Args:
        team: Team name (e.g., "Flamengo", "Corinthians")
        competition: Competition name (default "Brasileirão")
    """
    return get_team_performance_trend(_get_matches(), team, competition)


@mcp.tool()
def tool_get_data_summary() -> str:
    """Get a summary of the loaded datasets including match counts, seasons, competitions, and player counts."""
    return get_data_summary(_get_matches(), _get_players())


# ── Entry Point ─────────────────────────────────────────────────────────────


def main() -> None:
    """Run the MCP server."""
    logger.info("Starting Brazilian Soccer MCP Server...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()