"""
MCP stdio server for the Brazilian Soccer MCP Server.

This module uses ``mcp.server.fastmcp.FastMCP`` to expose the query engine as
a set of MCP tools. It communicates over standard input/output using the Model
Context Protocol, so it can be connected to any MCP client (Claude Desktop,
OpenCode, etc.).

Run directly for stdio mode:

    python -m brazilian_soccer_mcp.server

Or via the MCP CLI:

    mcp run brazilian_soccer_mcp.server
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from mcp.server.fastmcp import FastMCP

from .data_loader import load_all
from .engine import SoccerEngine

mcp = FastMCP("brazilian-soccer-mcp")

_engine: Optional[SoccerEngine] = None


def _get_engine() -> SoccerEngine:
    """Lazy load the engine so module import stays cheap during tests."""
    global _engine
    if _engine is None:
        data = load_all()
        _engine = SoccerEngine(data["matches"], data["players"])
    return _engine


@mcp.tool()
def find_matches(
    team1: Optional[str] = None,
    team2: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    date_from: Optional[str | date] = None,
    date_to: Optional[str | date] = None,
    round_number: Optional[str | int] = None,
    stage: Optional[str] = None,
    limit: int = 20,
) -> str:
    """Find matches by team, competition, season and date range."""
    return _get_engine().find_matches(
        team1=team1,
        team2=team2,
        competition=competition,
        season=season,
        date_from=date_from,
        date_to=date_to,
        round_=round_number,
        stage=stage,
        limit=limit,
    )


@mcp.tool()
def head_to_head(
    team1: str,
    team2: str,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 20,
) -> str:
    """Return fixtures and a summary between two teams."""
    return _get_engine().head_to_head(team1, team2, competition=competition, season=season, limit=limit)


@mcp.tool()
def team_statistics(
    team: str,
    season: Optional[int] = None,
    competition: Optional[str] = None,
) -> str:
    """Get overall, home and away statistics for a team."""
    return _get_engine().team_statistics(team, season=season, competition=competition)


@mcp.tool()
def team_competitions(team: str) -> str:
    """List the competitions and seasons a team has played in."""
    return _get_engine().team_competitions(team)


@mcp.tool()
def find_players(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    limit: int = 20,
) -> str:
    """Search the FIFA player dataset."""
    return _get_engine().find_players(name, nationality, club, position, limit=limit)


@mcp.tool()
def top_players(
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    limit: int = 10,
) -> str:
    """Return the highest-rated players, optionally filtered."""
    return _get_engine().top_players(nationality, club, position, limit=limit)


@mcp.tool()
def player_details(name: str) -> str:
    """Return details for a single player."""
    return _get_engine().player_details(name)


@mcp.tool()
def competition_standings(competition: str, season: int) -> str:
    """Return a final league table for a competition and season."""
    return _get_engine().competition_standings(competition, season)


@mcp.tool()
def relegated_teams(season: int) -> str:
    """Return the bottom four teams of the Brasileirão for a season."""
    return _get_engine().relegated_teams(season)


@mcp.tool()
def competition_finals(
    competition: str,
    season: Optional[int] = None,
    limit: int = 20,
) -> str:
    """Return the deepest-round matches for a knockout competition."""
    return _get_engine().competition_finals(competition, season=season, limit=limit)


@mcp.tool()
def biggest_wins(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 10,
) -> str:
    """Return the matches with the biggest goal difference."""
    return _get_engine().biggest_wins(competition, season, limit=limit)


@mcp.tool()
def average_goals(
    competition: Optional[str] = None,
    season: Optional[int] = None,
) -> str:
    """Return average goals per match and the home win rate."""
    return _get_engine().average_goals(competition, season)


@mcp.tool()
def best_away_record(min_matches: int = 10) -> str:
    """Rank teams by away win rate."""
    return _get_engine().best_away_record(min_matches=min_matches)


if __name__ == "__main__":
    mcp.run(transport="stdio")
