"""
Context Block
=============

Module: brazilian_soccer_mcp.server
Purpose: Create and run the MCP (Model Context Protocol) server that
         exposes the Brazilian soccer knowledge graph as a set of
         callable tools.

The server uses the official ``mcp`` Python SDK (v2.x, where
``FastMCP`` was renamed to ``MCPServer``).  Each tool corresponds to
a method on ``SoccerQueries`` and returns a JSON-serialisable dict.

Tools exposed
-------------
  Match:
    * find_matches          - search matches by team / opponent /
                              competition / season / date range
    * head_to_head          - head-to-head record between two teams

  Team:
    * team_statistics       - W/D/L and goals for a team
    * team_info             - overview of a team
    * compare_teams         - side-by-side comparison of two teams
    * best_home_record      - rank teams by home win rate
    * best_away_record      - rank teams by away win rate

  Player:
    * find_players          - search players by name / nationality /
                              club / position / rating
    * top_players           - top-rated players (with filters)
    * players_at_brazilian_clubs - players at Brazilian clubs

  Competition:
    * competition_standings  - calculated league table
    * competition_seasons    - available seasons
    * competition_info       - competition summary
    * all_competitions       - list all competitions

  Statistical:
    * biggest_wins           - biggest victory margins
    * average_goals          - goals-per-match statistics
    * home_vs_away           - home vs away performance
    * team_list              - list all teams
    * search_all             - cross-entity search

Run with ``python -m brazilian_soccer_mcp.server`` or the
``brazilian-soccer-mcp`` console script.
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Optional

from .data_loader import DataLoader, DEFAULT_DATA_DIR
from .knowledge_graph import KnowledgeGraph
from .queries import SoccerQueries

try:
    from mcp.server.mcpserver import MCPServer
    from mcp.types import TextContent
except ImportError:
    MCPServer = None  # type: ignore
    TextContent = None  # type: ignore


# ---------------------------------------------------------------------------
# Global singleton (loaded once, reused across tool calls)
# ---------------------------------------------------------------------------
_queries: Optional[SoccerQueries] = None


def get_queries(data_dir: str = DEFAULT_DATA_DIR) -> SoccerQueries:
    """Return the singleton ``SoccerQueries`` instance, loading data on first call."""
    global _queries
    if _queries is None:
        loader = DataLoader(data_dir=data_dir).load()
        graph = KnowledgeGraph(loader)
        _queries = SoccerQueries(graph)
    return _queries


def _result_to_text(result: dict) -> str:
    """Convert a dict result to a JSON text string for MCP."""
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


# ---------------------------------------------------------------------------
# Server factory
# ---------------------------------------------------------------------------
def create_server(name: str = "brazilian-soccer-mcp", data_dir: str = DEFAULT_DATA_DIR) -> "MCPServer":
    """Create and configure the MCP server with all tools.

    Parameters
    ----------
    name : str
        Server name.
    data_dir : str
        Directory containing the CSV data files.
    """
    if MCPServer is None:
        raise ImportError(
            "The 'mcp' package is required. Install it with: pip install mcp"
        )

    server = MCPServer(
        name=name,
        title="Brazilian Soccer MCP Server",
        description=(
            "MCP server providing a knowledge graph interface for "
            "Brazilian soccer data: matches, teams, players, and "
            "competitions from freely-available Kaggle datasets."
        ),
        version="2.0.0",
    )

    # Ensure data is loaded
    q = get_queries(data_dir=data_dir)

    # -- Match tools -------------------------------------------------------
    @server.tool()
    def find_matches(
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 50,
    ) -> str:
        """Find matches matching the given criteria.

        Args:
            team: Team name (any variant, e.g. "Flamengo", "Palmeiras-SP").
            opponent: Opposing team name.
            competition: Competition name (e.g. "Brasileirao", "Copa do Brasil").
            season: Season year (e.g. 2019).
            date_from: Start date (ISO, e.g. "2019-01-01").
            date_to: End date (ISO).
            limit: Maximum matches to return (default 50).

        Returns:
            JSON string with matches, count, and total_found.
        """
        result = q.find_matches(
            team=team, opponent=opponent, competition=competition,
            season=season, date_from=date_from, date_to=date_to, limit=limit,
        )
        return _result_to_text(result)

    @server.tool()
    def head_to_head(
        team1: str, team2: str, competition: Optional[str] = None
    ) -> str:
        """Compute the head-to-head record between two teams.

        Args:
            team1: First team name.
            team2: Second team name.
            competition: Optional competition filter.

        Returns:
            JSON string with wins/draws/losses and match list.
        """
        return _result_to_text(q.head_to_head(team1, team2, competition=competition))

    # -- Team tools --------------------------------------------------------
    @server.tool()
    def team_statistics(
        team: str, season: Optional[int] = None,
        competition: Optional[str] = None, venue: Optional[str] = None,
    ) -> str:
        """Compute statistics (W/D/L, goals) for a team.

        Args:
            team: Team name (any variant).
            season: Season year filter.
            competition: Competition name filter.
            venue: "home", "away", or None for all.

        Returns:
            JSON string with team statistics.
        """
        return _result_to_text(
            q.team_statistics(team, season=season, competition=competition, venue=venue)
        )

    @server.tool()
    def team_info(team: str) -> str:
        """Return overview information about a team.

        Args:
            team: Team name (any variant).

        Returns:
            JSON string with team info, competitions, and top players.
        """
        return _result_to_text(q.team_info(team))

    @server.tool()
    def compare_teams(team1: str, team2: str) -> str:
        """Compare two teams side by side.

        Args:
            team1: First team name.
            team2: Second team name.

        Returns:
            JSON string with both teams' info and head-to-head record.
        """
        return _result_to_text(q.compare_teams(team1, team2))

    @server.tool()
    def best_home_record(
        competition: Optional[str] = None, season: Optional[int] = None
    ) -> str:
        """Rank teams by home win rate.

        Args:
            competition: Competition name filter.
            season: Season year filter.

        Returns:
            JSON string with team rankings.
        """
        return _result_to_text(q.best_home_record(competition=competition, season=season))

    @server.tool()
    def best_away_record(
        competition: Optional[str] = None, season: Optional[int] = None
    ) -> str:
        """Rank teams by away win rate.

        Args:
            competition: Competition name filter.
            season: Season year filter.

        Returns:
            JSON string with team rankings.
        """
        return _result_to_text(q.best_away_record(competition=competition, season=season))

    # -- Player tools ------------------------------------------------------
    @server.tool()
    def find_players(
        name: Optional[str] = None, nationality: Optional[str] = None,
        club: Optional[str] = None, position: Optional[str] = None,
        min_rating: Optional[int] = None, max_rating: Optional[int] = None,
        limit: int = 50, sort_by: str = "overall",
    ) -> str:
        """Find players matching the given criteria.

        Args:
            name: Player name (substring, case-insensitive).
            nationality: Nationality (e.g. "Brazil").
            club: Club name (fuzzy matched).
            position: Position code (e.g. "ST", "GK", "LW").
            min_rating: Minimum overall rating.
            max_rating: Maximum overall rating.
            limit: Maximum players to return.
            sort_by: Field to sort by (default "overall").

        Returns:
            JSON string with player list.
        """
        return _result_to_text(
            q.find_players(
                name=name, nationality=nationality, club=club, position=position,
                min_rating=min_rating, max_rating=max_rating,
                limit=limit, sort_by=sort_by,
            )
        )

    @server.tool()
    def top_players(
        nationality: Optional[str] = None, club: Optional[str] = None,
        position: Optional[str] = None, limit: int = 10,
    ) -> str:
        """Return the top-rated players (optionally filtered).

        Args:
            nationality: Nationality filter.
            club: Club filter.
            position: Position filter.
            limit: Number of players to return (default 10).

        Returns:
            JSON string with top players.
        """
        return _result_to_text(
            q.top_players(nationality=nationality, club=club, position=position, limit=limit)
        )

    @server.tool()
    def players_at_brazilian_clubs(min_rating: int = 70, limit: int = 50) -> str:
        """Find players at Brazilian clubs (cross-references match data).

        Args:
            min_rating: Minimum overall rating (default 70).
            limit: Maximum players to return.

        Returns:
            JSON string with players at Brazilian clubs.
        """
        return _result_to_text(q.players_at_brazilian_clubs(min_rating=min_rating, limit=limit))

    # -- Competition tools -------------------------------------------------
    @server.tool()
    def competition_standings(
        competition: str, season: Optional[int] = None
    ) -> str:
        """Calculate league standings from match results.

        Args:
            competition: Competition name (e.g. "Brasileirao").
            season: Season year. If None, aggregates all seasons.

        Returns:
            JSON string with standings table and champion.
        """
        return _result_to_text(q.competition_standings(competition, season=season))

    @server.tool()
    def competition_seasons(competition: str) -> str:
        """List all seasons available for a competition.

        Args:
            competition: Competition name.

        Returns:
            JSON string with seasons list.
        """
        return _result_to_text(q.competition_seasons(competition))

    @server.tool()
    def competition_info(competition: str) -> str:
        """Return summary information about a competition.

        Args:
            competition: Competition name.

        Returns:
            JSON string with competition summary.
        """
        return _result_to_text(q.competition_info(competition))

    @server.tool()
    def all_competitions() -> str:
        """List all competitions with summary information.

        Returns:
            JSON string with all competitions.
        """
        return _result_to_text(q.all_competitions())

    # -- Statistical tools -------------------------------------------------
    @server.tool()
    def biggest_wins(
        competition: Optional[str] = None, season: Optional[int] = None, limit: int = 10
    ) -> str:
        """Find the biggest victory margins in the dataset.

        Args:
            competition: Competition filter.
            season: Season filter.
            limit: Number of results (default 10).

        Returns:
            JSON string with biggest wins.
        """
        return _result_to_text(q.biggest_wins(competition=competition, season=season, limit=limit))

    @server.tool()
    def average_goals(
        competition: Optional[str] = None, season: Optional[int] = None
    ) -> str:
        """Calculate average goals per match and scoring statistics.

        Args:
            competition: Competition filter.
            season: Season filter.

        Returns:
            JSON string with goal statistics.
        """
        return _result_to_text(q.average_goals(competition=competition, season=season))

    @server.tool()
    def home_vs_away(
        competition: Optional[str] = None, season: Optional[int] = None
    ) -> str:
        """Compare home vs away performance across all matches.

        Args:
            competition: Competition filter.
            season: Season filter.

        Returns:
            JSON string with home vs away statistics.
        """
        return _result_to_text(q.home_vs_away(competition=competition, season=season))

    @server.tool()
    def team_list(search: Optional[str] = None, limit: int = 50) -> str:
        """List all teams (optionally filtered by search string).

        Args:
            search: Search string for team names.
            limit: Maximum teams to return.

        Returns:
            JSON string with team list.
        """
        return _result_to_text(q.team_list(search=search, limit=limit))

    @server.tool()
    def search_all(query: str) -> str:
        """Search across teams, players, and competitions by name.

        Args:
            query: Search query.

        Returns:
            JSON string with matching teams, players, and competitions.
        """
        return _result_to_text(q.search_all(query))

    return server


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------
def main() -> None:
    """Run the MCP server over stdio."""
    server = create_server()
    asyncio.run(server.run_stdio_async())


if __name__ == "__main__":
    main()
