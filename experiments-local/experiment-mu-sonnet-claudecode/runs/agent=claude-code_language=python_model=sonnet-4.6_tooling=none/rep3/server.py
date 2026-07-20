"""Brazilian Soccer MCP Server."""

from typing import Optional

import fastmcp

import data_loader as dl

mcp = fastmcp.FastMCP(
    name="Brazilian Soccer MCP",
    instructions=(
        "Knowledge graph server for Brazilian soccer data. "
        "Covers Brasileirão Serie A, Copa do Brasil, Copa Libertadores, and FIFA player data."
    ),
)


@mcp.tool()
def find_matches(
    team1: Optional[str] = None,
    team2: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 20,
) -> list[dict]:
    """Find soccer matches. Filter by team(s), competition, season, or date range.

    Args:
        team1: First team name (e.g. "Flamengo")
        team2: Second team name — when both provided, finds matches between them
        competition: Competition name (e.g. "Brasileirao", "Copa do Brasil", "Libertadores")
        season: Year (e.g. 2023)
        date_from: Start date ISO format (e.g. "2023-01-01")
        date_to: End date ISO format (e.g. "2023-12-31")
        limit: Max number of results (default 20, max 100)
    """
    return dl.find_matches(
        team1=team1,
        team2=team2,
        competition=competition,
        season=season,
        date_from=date_from,
        date_to=date_to,
        limit=min(limit, 100),
    )


@mcp.tool()
def get_team_statistics(
    team: str,
    competition: Optional[str] = None,
    season: Optional[int] = None,
) -> dict:
    """Get win/draw/loss statistics for a team, optionally filtered by competition and season.

    Args:
        team: Team name (e.g. "Palmeiras")
        competition: Filter by competition (e.g. "Brasileirao")
        season: Filter by season year (e.g. 2022)
    """
    return dl.get_team_stats(team=team, competition=competition, season=season)


@mcp.tool()
def get_head_to_head(
    team1: str,
    team2: str,
    limit: int = 20,
) -> dict:
    """Get head-to-head record and recent matches between two teams.

    Args:
        team1: First team name (e.g. "Flamengo")
        team2: Second team name (e.g. "Fluminense")
        limit: Max number of recent matches to return (default 20)
    """
    return dl.get_head_to_head(team1=team1, team2=team2, limit=min(limit, 50))


@mcp.tool()
def find_players(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    limit: int = 20,
) -> list[dict]:
    """Search FIFA player database. Filter by name, nationality, club, or position.

    Args:
        name: Player name search (e.g. "Neymar")
        nationality: Nationality filter (e.g. "Brazil")
        club: Club filter (e.g. "Flamengo")
        position: Position filter (e.g. "ST", "GK", "CB")
        min_overall: Minimum FIFA overall rating (e.g. 80)
        limit: Max results (default 20)
    """
    return dl.find_players(
        name=name,
        nationality=nationality,
        club=club,
        position=position,
        min_overall=min_overall,
        limit=min(limit, 100),
    )


@mcp.tool()
def get_standings(
    season: int,
    competition: str = "Brasileirao",
) -> list[dict]:
    """Calculate standings table for a given season and competition (based on match results).

    Args:
        season: Season year (e.g. 2019)
        competition: Competition name (default "Brasileirao")
    """
    return dl.get_standings(season=season, competition=competition)


@mcp.tool()
def get_biggest_wins(
    competition: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    """Get matches with the largest goal differences (biggest victories).

    Args:
        competition: Filter by competition (optional)
        limit: Number of results (default 10)
    """
    return dl.get_biggest_wins(competition=competition, limit=min(limit, 50))


@mcp.tool()
def get_dataset_summary(
    competition: Optional[str] = None,
) -> dict:
    """Get overall statistics and summary for the dataset.

    Args:
        competition: Filter to a specific competition (optional)
    """
    return dl.get_competition_summary(competition=competition)


if __name__ == "__main__":
    mcp.run()
