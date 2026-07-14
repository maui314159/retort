"""
Brazilian Soccer MCP Server
=============================
MCP (Model Context Protocol) server providing query tools for Brazilian
soccer match, team, player, competition, and statistical data.

Uses FastMCP from the mcp Python package.

Tools exposed:
  - find_matches: Search matches by team, competition, season, date range
  - team_stats: Get team statistics (wins, losses, goals, home/away records)
  - head_to_head: Compare two teams head-to-head
  - find_players: Search FIFA player database
  - competition_standings: Calculate competition standings
  - average_goals: Statistical summary
  - biggest_wins: Find biggest victories
  - season_comparison: Compare two seasons
  - most_goals_team: Find top-scoring teams
  - brazilian_players_summary: Summary of Brazilian players
  - competitions_for_team: List all competitions a team played in
  - best_home_record: Teams with best home record
  - best_away_record: Teams with best away record
"""

from typing import Optional

from mcp.server.fastmcp import FastMCP

from query_engine import QueryEngine

# ---------------------------------------------------------------------------
# Server setup
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "brazilian-soccer-mcp",
    instructions=(
        "Brazilian Soccer MCP Server - Query match, team, player, competition, "
        "and statistical data from Brazilian soccer datasets."
    ),
)

_engine = QueryEngine()


# ---------------------------------------------------------------------------
# 1. Match Queries
# ---------------------------------------------------------------------------

@mcp.tool(description="Find matches by team, competition, season, or date range")
def find_matches(
    team: Optional[str] = None,
    team2: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 50,
) -> str:
    """
    Find matches by criteria.

    Args:
        team: Team name to search for (home or away)
        team2: Second team for head-to-head queries
        competition: Filter by competition name (e.g., "Brasileirao", "Copa do Brasil")
        season: Filter by season year (e.g., 2023)
        date_from: Start date in YYYY-MM-DD format
        date_to: End date in YYYY-MM-DD format
        limit: Maximum number of results to return
    """
    return _engine.find_matches(
        team=team, team2=team2, competition=competition,
        season=season, date_from=date_from, date_to=date_to, limit=limit,
    )


# ---------------------------------------------------------------------------
# 2. Team Queries
# ---------------------------------------------------------------------------

@mcp.tool(description="Get team statistics including wins, losses, draws, goals, and home/away records")
def team_stats(
    team: str,
    season: Optional[int] = None,
    competition: Optional[str] = None,
) -> str:
    """
    Get comprehensive statistics for a team.

    Args:
        team: Team name (e.g., "Flamengo", "Palmeiras")
        season: Optional season year filter
        competition: Optional competition filter
    """
    return _engine.team_stats(team=team, season=season, competition=competition)


@mcp.tool(description="Compare two teams head-to-head with match history and statistics")
def head_to_head(team1: str, team2: str) -> str:
    """
    Compare two teams head-to-head.

    Args:
        team1: First team name
        team2: Second team name
    """
    return _engine.head_to_head(team1=team1, team2=team2)


@mcp.tool(description="Find teams with the best home record")
def best_home_record(
    season: Optional[int] = None,
    competition: str = "Brasileirao",
) -> str:
    """
    Find teams with the best home record.

    Args:
        season: Optional season filter
        competition: Competition name (default: Brasileirao)
    """
    return _engine.best_home_record(season=season, competition=competition)


@mcp.tool(description="Find teams with the best away record")
def best_away_record(
    season: Optional[int] = None,
    competition: str = "Brasileirao",
) -> str:
    """
    Find teams with the best away record.

    Args:
        season: Optional season filter
        competition: Competition name (default: Brasileirao)
    """
    return _engine.best_away_record(season=season, competition=competition)


# ---------------------------------------------------------------------------
# 3. Player Queries
# ---------------------------------------------------------------------------

@mcp.tool(description="Find FIFA players by name, nationality, club, position, or rating")
def find_players(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    limit: int = 20,
) -> str:
    """
    Find players in the FIFA database.

    Args:
        name: Player name substring search
        nationality: Filter by nationality (e.g., "Brazil", "Argentina")
        club: Filter by club name
        position: Filter by position (e.g., "ST", "LW", "GK", "CDM")
        min_overall: Minimum FIFA overall rating
        limit: Maximum results to return
    """
    return _engine.find_players(
        name=name, nationality=nationality, club=club,
        position=position, min_overall=min_overall, limit=limit,
    )


@mcp.tool(description="Get summary of Brazilian players in the database with top players and club breakdowns")
def brazilian_players_summary() -> str:
    """Get a summary of Brazilian players in the FIFA database."""
    return _engine.brazilian_players_summary()


# ---------------------------------------------------------------------------
# 4. Competition Queries
# ---------------------------------------------------------------------------

@mcp.tool(description="Calculate competition standings from match results")
def competition_standings(
    competition: str = "Brasileirao",
    season: Optional[int] = None,
) -> str:
    """
    Calculate league standings from match results.

    Args:
        competition: Competition name (e.g., "Brasileirao", "Copa do Brasil")
        season: Season year
    """
    return _engine.competition_standings(competition=competition, season=season)


@mcp.tool(description="List all competitions a team has participated in")
def competitions_for_team(team: str) -> str:
    """
    List all competitions a team has played in.

    Args:
        team: Team name
    """
    return _engine.competitions_for_team(team=team)


# ---------------------------------------------------------------------------
# 5. Statistical Analysis
# ---------------------------------------------------------------------------

@mcp.tool(description="Calculate average goals per match, home/away win rates, and other statistics")
def average_goals(
    competition: Optional[str] = None,
    season: Optional[int] = None,
) -> str:
    """
    Calculate statistical summary including average goals per match
    and win rates.

    Args:
        competition: Optional competition filter
        season: Optional season filter
    """
    return _engine.average_goals(competition=competition, season=season)


@mcp.tool(description="Find the biggest wins (largest goal differences) in the dataset")
def biggest_wins(
    competition: Optional[str] = None,
    limit: int = 10,
) -> str:
    """
    Find the biggest victories by goal difference.

    Args:
        competition: Optional competition filter
        limit: Number of results (default 10)
    """
    return _engine.biggest_wins(competition=competition, limit=limit)


@mcp.tool(description="Compare statistics between two different seasons")
def season_comparison(
    season1: int,
    season2: int,
    competition: str = "Brasileirao",
) -> str:
    """
    Compare statistics between two seasons.

    Args:
        season1: First season year (e.g., 2018)
        season2: Second season year (e.g., 2019)
        competition: Competition name (default: Brasileirao)
    """
    return _engine.season_comparison(
        season1=season1, season2=season2, competition=competition,
    )


@mcp.tool(description="Find which team scored the most goals in a competition/season")
def most_goals_team(
    season: Optional[int] = None,
    competition: str = "Brasileirao",
) -> str:
    """
    Find which team scored the most goals.

    Args:
        season: Optional season filter
        competition: Competition name (default: Brasileirao)
    """
    return _engine.most_goals_team(season=season, competition=competition)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    """Run the MCP server via stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()