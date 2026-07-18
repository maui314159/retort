"""
brazilian_soccer_mcp.server
===========================

MCP (Model Context Protocol) server that exposes the Brazilian soccer
knowledge graph as LLM-callable tools.

Context
-------
This module wraps the :class:`QueryEngine` in MCP tools using the FastMCP
framework. An LLM connected to this server can call these tools to answer
natural-language questions about Brazilian soccer.

The server loads all datasets once at startup (≈4 s for ~17 000 matches +
18 000 players) and serves every subsequent query from the in-memory graph.

Running
-------
    # via module
    python -m brazilian_soccer_mcp

    # via script
    python server.py

    # via MCP client (e.g. Claude Desktop config)
    {
      "mcpServers": {
        "brazilian-soccer": {
          "command": "python",
          "args": ["-m", "brazilian_soccer_mcp"]
        }
      }
    }
"""

from __future__ import annotations

import sys
from functools import lru_cache
from typing import Optional

from mcp.server.fastmcp import FastMCP

from .data_loader import LoadedData, load_datasets
from .knowledge_graph import KnowledgeGraph
from .query_engine import QueryEngine

# ---------------------------------------------------------------------------
# Singleton initialisation (loaded once, reused for every tool call)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _get_engine() -> QueryEngine:
    """Build and cache the query engine (loads all CSV data on first call)."""
    data: LoadedData = load_datasets()
    graph: KnowledgeGraph = KnowledgeGraph(data)
    return QueryEngine(graph)


# ---------------------------------------------------------------------------
# FastMCP server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="brazilian-soccer-mcp",
    instructions=(
        "Brazilian Soccer knowledge graph. Query matches, teams, players, "
        "competitions, and statistics from Brazilian soccer datasets "
        "(Brasileirão, Copa do Brasil, Copa Libertadores, FIFA players). "
        "Team names are normalised — you can use 'Flamengo', 'Flamengo-RJ', "
        "or 'Flamengo - RJ' interchangeably."
    ),
)


# == Match Queries ==


@mcp.tool()
def search_matches(
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
) -> str:
    """Search matches by team, opponent, competition, season, or date range.

    Args:
        team: Team name (home or away). Accepts variations like "Flamengo".
        opponent: Opposing team name.
        competition: Competition name (Brasileirão, Copa do Brasil, Libertadores).
        season: Year of the season (e.g. 2023).
        start_date: Start date (YYYY-MM-DD).
        end_date: End date (YYYY-MM-DD).
        limit: Max matches to return (default 50).
    """
    return _get_engine().search_matches(
        team=team, opponent=opponent, competition=competition, season=season,
        start_date=start_date, end_date=end_date, limit=limit,
    )


@mcp.tool()
def head_to_head(team_a: str, team_b: str) -> str:
    """Get head-to-head record between two teams.

    Args:
        team_a: First team name.
        team_b: Second team name.
    """
    return _get_engine().head_to_head(team_a, team_b)


# == Team Queries ==


@mcp.tool()
def team_statistics(
    team: str,
    season: Optional[int] = None,
    competition: Optional[str] = None,
    venue: Optional[str] = None,
) -> str:
    """Get win/loss/draw record and goals for a team.

    Args:
        team: Team name.
        season: Filter by season year.
        competition: Filter by competition.
        venue: "home", "away", or None for all matches.
    """
    return _get_engine().team_statistics(
        team=team, season=season, competition=competition, venue=venue,
    )


@mcp.tool()
def compare_teams(team_a: str, team_b: str) -> str:
    """Compare two teams head-to-head with full statistics.

    Args:
        team_a: First team name.
        team_b: Second team name.
    """
    return _get_engine().compare_teams(team_a, team_b)


@mcp.tool()
def team_competitions(team: str) -> str:
    """List all competitions a team has participated in.

    Args:
        team: Team name.
    """
    return _get_engine().competitions_for_team(team)


# == Player Queries ==


@mcp.tool()
def search_players(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    is_forward: bool = False,
    limit: int = 20,
) -> str:
    """Search the FIFA player database by name, nationality, club, or position.

    Args:
        name: Player name (substring match).
        nationality: Nationality (e.g. "Brazil").
        club: Club name.
        position: Playing position (e.g. "ST", "LW", "GK").
        min_overall: Minimum FIFA overall rating.
        is_forward: If True, filter to forward positions only.
        limit: Max players to return (default 20).
    """
    return _get_engine().search_players(
        name=name, nationality=nationality, club=club, position=position,
        min_overall=min_overall, is_forward=is_forward, limit=limit,
    )


@mcp.tool()
def top_players_at_club(club: str, limit: int = 10) -> str:
    """Get the highest-rated players at a given club.

    Args:
        club: Club name.
        limit: Max players to return (default 10).
    """
    return _get_engine().top_players_at_club(club, limit)


@mcp.tool()
def top_brazilian_players(limit: int = 20) -> str:
    """Get the top-rated Brazilian players in the dataset.

    Args:
        limit: Max players to return (default 20).
    """
    return _get_engine().top_brazilian_players(limit)


# == Competition Queries ==


@mcp.tool()
def standings(competition: str, season: int, top_n: int = 20) -> str:
    """Get calculated standings for a competition and season.

    Args:
        competition: Competition name (e.g. "Brasileirão").
        season: Season year (e.g. 2019).
        top_n: Number of top teams to return (default 20).
    """
    return _get_engine().standings(competition, season, top_n)


@mcp.tool()
def competition_info(competition: str) -> str:
    """Get overview of a competition (seasons, match count, teams).

    Args:
        competition: Competition name.
    """
    return _get_engine().competition_info(competition)


# == Statistical Analysis ==


@mcp.tool()
def average_goals(
    competition: Optional[str] = None,
    season: Optional[int] = None,
) -> str:
    """Get average goals per match and home/away win rates.

    Args:
        competition: Filter by competition.
        season: Filter by season year.
    """
    return _get_engine().average_goals(competition=competition, season=season)


@mcp.tool()
def biggest_wins(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 10,
) -> str:
    """Get the biggest victories by goal difference.

    Args:
        competition: Filter by competition.
        season: Filter by season year.
        limit: Max results (default 10).
    """
    return _get_engine().biggest_wins(competition=competition, season=season, limit=limit)


@mcp.tool()
def best_records(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    venue: Optional[str] = None,
    metric: str = "win_rate",
    limit: int = 10,
) -> str:
    """Rank teams by win rate or goals scored.

    Args:
        competition: Filter by competition.
        season: Filter by season year.
        venue: "home", "away", or None for all.
        metric: "win_rate" or "goals".
        limit: Max teams to return (default 10).
    """
    return _get_engine().best_records(
        competition=competition, season=season, venue=venue,
        metric=metric, limit=limit,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the MCP server on stdio (standard MCP transport)."""
    mcp.run()


if __name__ == "__main__":
    main()
