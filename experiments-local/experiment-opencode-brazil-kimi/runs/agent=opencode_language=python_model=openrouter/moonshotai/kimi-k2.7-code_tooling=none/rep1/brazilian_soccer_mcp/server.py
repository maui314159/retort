"""MCP server exposing Brazilian soccer knowledge graph tools."""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

from .knowledge_graph import get_knowledge_graph

INSTRUCTIONS = (
    "You are an assistant for Brazilian soccer data. Use the available tools to "
    "answer questions about matches, teams, players, competitions and statistics. "
    "When a question is ambiguous, ask the user for clarification or use sensible "
    "defaults (e.g., Brasileirão for league questions)."
)

mcp = FastMCP("brazilian-soccer-mcp", instructions=INSTRUCTIONS)


def _kg():
    return get_knowledge_graph()


@mcp.tool()
def search_matches(
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 20,
) -> str:
    """Search for matches by team, opponent, competition, season and/or date range."""
    return _kg().search_matches(team, opponent, competition, season, from_date, to_date, limit)


@mcp.tool()
def get_head_to_head(
    team_a: str,
    team_b: str,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 20,
) -> str:
    """Return the head-to-head record and recent matches between two teams."""
    return _kg().get_head_to_head(team_a, team_b, competition, season, limit)


@mcp.tool()
def get_team_stats(
    team: str,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    venue: Optional[str] = None,
) -> str:
    """Return wins, draws, losses, goals and win rate for a team."""
    return _kg().get_team_stats(team, competition, season, venue)


@mcp.tool()
def get_competition_standings(
    competition: str,
    season: Optional[int] = None,
    limit: Optional[int] = None,
) -> str:
    """Compute a league table from match results."""
    return _kg().get_competition_standings(competition, season, limit)


@mcp.tool()
def get_top_scoring_teams(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 10,
) -> str:
    """Return the teams with the most goals scored."""
    return _kg().get_top_scoring_teams(competition, season, limit)


@mcp.tool()
def get_biggest_wins(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 10,
) -> str:
    """Return matches with the largest goal difference."""
    return _kg().get_biggest_wins(competition, season, limit)


@mcp.tool()
def get_average_goals(
    competition: Optional[str] = None,
    season: Optional[int] = None,
) -> str:
    """Return average goals per match and home win rate."""
    return _kg().get_average_goals(competition, season)


@mcp.tool()
def list_competitions() -> str:
    """List all available competitions in the dataset."""
    return _kg().list_competitions()


@mcp.tool()
def list_seasons(competition: Optional[str] = None) -> str:
    """List available seasons, optionally filtered by competition."""
    return _kg().list_seasons(competition)


@mcp.tool()
def search_players(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    limit: int = 20,
) -> str:
    """Search the FIFA player database by name, nationality, club, position or rating."""
    return _kg().search_players(name, nationality, club, position, min_overall, limit)
