"""
Brazilian Soccer MCP Server

Exposes six tools for querying Brazilian soccer data loaded from local CSV files.
Run with: python server.py  (stdio transport, connect via any MCP client)
"""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

from data_loader import get_store
import queries as q

mcp = FastMCP(
    "Brazilian Soccer",
    instructions=(
        "This server provides tools to query Brazilian soccer data covering "
        "Brasileirão Série A, Copa do Brasil, Copa Libertadores matches, "
        "historical Brasileirão data (2003-2019), and FIFA player ratings. "
        "Use find_matches for match lookups, get_team_stats for records, "
        "find_players for player search, get_standings for league tables, "
        "get_biggest_wins for top victories, get_competition_stats for "
        "aggregate numbers, and get_best_records for team rankings by win rate."
    ),
)


# ---------------------------------------------------------------------------
# Tool 1: Find Matches
# ---------------------------------------------------------------------------

@mcp.tool()
def find_matches(
    team: Optional[str] = None,
    team2: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 30,
) -> str:
    """
    Find matches with optional filters.

    When two teams are provided, returns head-to-head history with a summary.
    Competition names can be partial: "brasileirao", "copa", "libertadores".
    Dates should be in YYYY-MM-DD format.

    Args:
        team: First team name to search for (partial match supported)
        team2: Second team name for head-to-head queries
        competition: Competition name filter (partial, case-insensitive)
        season: Year of the season
        date_from: Start date filter (YYYY-MM-DD)
        date_to: End date filter (YYYY-MM-DD)
        limit: Maximum number of matches to display (default 30)
    """
    store = get_store()
    return q.find_matches(
        store,
        team=team,
        team2=team2,
        competition=competition,
        season=season,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# Tool 2: Team Statistics
# ---------------------------------------------------------------------------

@mcp.tool()
def get_team_stats(
    team: str,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    home_only: bool = False,
    away_only: bool = False,
) -> str:
    """
    Get win/loss/draw record and goals statistics for a team.

    Args:
        team: Team name (partial match supported)
        competition: Filter by competition (partial, case-insensitive)
        season: Filter by year
        home_only: Show only home matches
        away_only: Show only away matches
    """
    store = get_store()
    return q.get_team_stats(
        store,
        team=team,
        competition=competition,
        season=season,
        home_only=home_only,
        away_only=away_only,
    )


# ---------------------------------------------------------------------------
# Tool 3: Player Search
# ---------------------------------------------------------------------------

@mcp.tool()
def find_players(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_rating: Optional[int] = None,
    limit: int = 20,
) -> str:
    """
    Search the FIFA player database by name, nationality, club, or position.
    Players are sorted by overall rating descending.

    Args:
        name: Player name (partial match)
        nationality: Nationality filter (e.g. "Brazilian", "Brazil")
        club: Club name filter (e.g. "Flamengo", "Palmeiras")
        position: Position filter (e.g. "GK", "ST", "CAM")
        min_rating: Minimum overall rating
        limit: Maximum number of players to return (default 20)
    """
    store = get_store()
    return q.find_players(
        store,
        name=name,
        nationality=nationality,
        club=club,
        position=position,
        min_rating=min_rating,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# Tool 4: Season Standings
# ---------------------------------------------------------------------------

@mcp.tool()
def get_standings(
    season: int,
    competition: str = "Brasileirão Série A",
) -> str:
    """
    Calculate and display league standings for a given season,
    computed from actual match results in the dataset.

    Args:
        season: Year (e.g. 2019)
        competition: Competition name (default: "Brasileirão Série A")
    """
    store = get_store()
    return q.get_standings(store, season=season, competition=competition)


# ---------------------------------------------------------------------------
# Tool 5: Biggest Wins
# ---------------------------------------------------------------------------

@mcp.tool()
def get_biggest_wins(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 10,
) -> str:
    """
    Return the biggest victories (by goal margin) in the dataset.

    Args:
        competition: Filter by competition name (partial)
        season: Filter by season year
        limit: Number of results to return (default 10)
    """
    store = get_store()
    return q.get_biggest_wins(store, competition=competition, season=season, limit=limit)


# ---------------------------------------------------------------------------
# Tool 6: Competition Overview Statistics
# ---------------------------------------------------------------------------

@mcp.tool()
def get_competition_stats(
    competition: Optional[str] = None,
    season: Optional[int] = None,
) -> str:
    """
    Return aggregate statistics for a competition and/or season:
    total matches, goals, average goals per match, home/away/draw percentages.

    Args:
        competition: Competition name filter (partial, e.g. "brasileirao")
        season: Season year filter
    """
    store = get_store()
    return q.get_competition_stats(store, competition=competition, season=season)


# ---------------------------------------------------------------------------
# Tool 7: Best Records
# ---------------------------------------------------------------------------

@mcp.tool()
def get_best_records(
    record_type: str = "home",
    competition: Optional[str] = None,
    season: Optional[int] = None,
    min_matches: int = 10,
    limit: int = 10,
) -> str:
    """
    Rank teams by win rate for home, away, or overall performance.

    Args:
        record_type: One of "home", "away", or "overall"
        competition: Competition name filter (partial)
        season: Season year filter
        min_matches: Minimum matches required to appear in ranking (default 10)
        limit: Number of teams to return (default 10)
    """
    store = get_store()
    return q.get_best_records(
        store,
        record_type=record_type,
        competition=competition,
        season=season,
        min_matches=min_matches,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
