"""
Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server exposing Brazilian soccer data
through query tools.  Backed by data_loader.py which loads and normalises
the six Kaggle CSV datasets at startup.

Context:
  TASK.md §"Required Capabilities" defines five query categories:
  match queries, team queries, player queries, competition queries,
  and statistical analysis.  Each maps to one or more MCP tools below.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from data_loader import (
    get_competition_standings,
    get_head_to_head,
    get_statistics,
    get_team_stats,
    list_competitions,
    list_seasons,
    list_teams,
    search_matches,
    search_players,
)

mcp = FastMCP("brazilian-soccer-mcp")


# ---------------------------------------------------------------------------
# 1. Match Queries
# ---------------------------------------------------------------------------


@mcp.tool()
def query_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """Search matches across all Brazilian soccer datasets.

    Find matches by team, opponent, competition, season, or date range.
    Returns matches sorted by date descending.

    Examples:
      - query_matches(team="Flamengo", opponent="Fluminense")
      - query_matches(team="Palmeiras", season=2023)
      - query_matches(competition="Copa do Brasil", season=2022)
    """
    return search_matches(
        team=team,
        opponent=opponent,
        competition=competition,
        season=season,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# 2. Team Queries
# ---------------------------------------------------------------------------


@mcp.tool()
def team_statistics(
    team: str,
    competition: str | None = None,
    season: int | None = None,
) -> dict:
    """Get win/draw/loss record and goal stats for a team.

    Optionally filter by competition and/or season.

    Examples:
      - team_statistics(team="Corinthians", season=2022)
      - team_statistics(team="Palmeiras", competition="Libertadores")
    """
    return get_team_stats(team=team, competition=competition, season=season)


@mcp.tool()
def head_to_head(
    team_a: str,
    team_b: str,
    limit: int = 50,
) -> dict:
    """Compare two teams head-to-head across all match data.

    Returns per-team win counts, draws, and the individual match results.

    Examples:
      - head_to_head(team_a="Palmeiras", team_b="Santos")
      - head_to_head(team_a="Flamengo", team_b="Fluminense")
    """
    return get_head_to_head(team_a=team_a, team_b=team_b, limit=limit)


# ---------------------------------------------------------------------------
# 3. Player Queries
# ---------------------------------------------------------------------------


@mcp.tool()
def query_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    limit: int = 50,
) -> list[dict]:
    """Search FIFA player data with flexible filters.

    Filter by name, nationality, club, position, or minimum overall rating.
    Results sorted by overall rating descending.

    Examples:
      - query_players(nationality="Brazil")
      - query_players(club="Flamengo")
      - query_players(position="ST", min_overall=80)
    """
    return search_players(
        name=name,
        nationality=nationality,
        club=club,
        position=position,
        min_overall=min_overall,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# 4. Competition Queries
# ---------------------------------------------------------------------------


@mcp.tool()
def competition_standings(
    competition: str,
    season: int,
) -> list[dict]:
    """Calculate standings for a competition and season from match results.

    Uses 3-1-0 point system. Best suited for round-robin leagues.

    Examples:
      - competition_standings(competition="Brasileirão", season=2019)
      - competition_standings(competition="Copa do Brasil", season=2022)
    """
    return get_competition_standings(competition=competition, season=season)


@mcp.tool()
def available_competitions() -> list[str]:
    """List all competition names available in the dataset."""
    return list_competitions()


@mcp.tool()
def available_seasons(competition: str | None = None) -> list[int]:
    """List all seasons (years) available, optionally filtered by competition."""
    return list_seasons(competition=competition)


# ---------------------------------------------------------------------------
# 5. Statistical Analysis
# ---------------------------------------------------------------------------


@mcp.tool()
def match_statistics(
    competition: str | None = None,
    season: int | None = None,
) -> dict:
    """Get aggregate match statistics: avg goals, home win rate, biggest wins.

    Optionally filter by competition and/or season.

    Examples:
      - match_statistics(competition="Brasileirão")
      - match_statistics(competition="Libertadores", season=2019)
    """
    return get_statistics(competition=competition, season=season)


@mcp.tool()
def available_teams(competition: str | None = None) -> list[str]:
    """List all team names in the dataset, optionally filtered by competition."""
    return list_teams(competition=competition)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
