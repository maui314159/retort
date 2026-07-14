"""MCP server exposing Brazilian soccer query tools.

Context block
-------------
This module wraps the query functions in ``queries.py`` as MCP tools that an
LLM client can invoke. It uses the ``fastmcp`` library (which implements the
Model Context Protocol) and exposes one tool per query category described in
``TASK.md``:

  * ``find_matches``            - search matches by team/opponent/competition/season/date
  * ``head_to_head``            - head-to-head record between two teams
  * ``team_statistics``         - win/draw/loss + goals for a team
  * ``compare_teams``           - side-by-side comparison of two teams
  * ``search_players``          - search the FIFA player dataset
  * ``top_players_at_club``     - highest-rated players at a club
  * ``competition_standings``   - calculated standings for a competition+season
  * ``list_competitions``       - available competitions in the dataset
  * ``competition_seasons``     - seasons available for a competition
  * ``average_goals``           - average goals per match + home win rate
  * ``biggest_wins``            - largest victory margins
  * ``home_vs_away_record``     - home/away split for a team
  * ``last_match_between``      - most recent match between two teams

Run with ``python -m brazilian_soccer_mcp.server`` or the
``brazilian-soccer-mcp`` console script.
"""
from __future__ import annotations

import json
from typing import Optional

from fastmcp import FastMCP

from .data_loader import DataLoader, get_loader
from . import queries as q


def _ensure_loader(loader: Optional[DataLoader] = None) -> DataLoader:
    return loader if loader is not None else get_loader()


def create_server(loader: Optional[DataLoader] = None) -> FastMCP:
    """Create and configure the FastMCP server with all soccer tools."""
    mcp = FastMCP("Brazilian Soccer MCP")

    @mcp.tool()
    def find_matches(
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> str:
        """Find matches matching the given criteria. Any omitted argument is a wildcard.

        Use ``team``+``opponent`` for head-to-head fixtures; ``competition``
        accepts substrings like 'Brasileirao', 'Copa do Brasil', 'Libertadores'.
        Dates are ISO 'YYYY-MM-DD'.
        """
        result = q.find_matches(
            _ensure_loader(loader), team, opponent, competition, season,
            start_date, end_date, limit,
        )
        return json.dumps(result, ensure_ascii=False, default=str)

    @mcp.tool()
    def head_to_head(team_a: str, team_b: str, competition: Optional[str] = None) -> str:
        """Return the head-to-head record between two teams."""
        result = q.find_head_to_head(_ensure_loader(loader), team_a, team_b, competition)
        return json.dumps(result, ensure_ascii=False, default=str)

    @mcp.tool()
    def team_statistics(
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        venue: Optional[str] = None,
    ) -> str:
        """Compute win/draw/loss and goal statistics for a team.

        ``venue`` may be 'home', 'away' or None (both).
        """
        result = q.team_statistics(
            _ensure_loader(loader), team, season, competition, venue
        )
        return json.dumps(result, ensure_ascii=False, default=str)

    @mcp.tool()
    def compare_teams(
        team_a: str, team_b: str, season: Optional[int] = None
    ) -> str:
        """Compare two teams side-by-side and head-to-head."""
        result = q.compare_teams(_ensure_loader(loader), team_a, team_b, season)
        return json.dumps(result, ensure_ascii=False, default=str)

    @mcp.tool()
    def search_players(
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        limit: Optional[int] = 50,
    ) -> str:
        """Search the FIFA player dataset by name, nationality, club, position or rating."""
        result = q.search_players(
            _ensure_loader(loader), name, nationality, club, position, min_overall, limit
        )
        return json.dumps(result, ensure_ascii=False, default=str)

    @mcp.tool()
    def top_players_at_club(club: str, limit: int = 10) -> str:
        """Return the highest-rated players at a given club."""
        result = q.top_players_at_club(_ensure_loader(loader), club, limit)
        return json.dumps(result, ensure_ascii=False, default=str)

    @mcp.tool()
    def competition_standings(competition: str, season: int) -> str:
        """Calculate standings for a competition+season from match results."""
        result = q.competition_standings(_ensure_loader(loader), competition, season)
        return json.dumps(result, ensure_ascii=False, default=str)

    @mcp.tool()
    def list_competitions() -> str:
        """List all competitions available in the dataset."""
        result = q.list_competitions(_ensure_loader(loader))
        return json.dumps(result, ensure_ascii=False, default=str)

    @mcp.tool()
    def competition_seasons(competition: str) -> str:
        """List seasons available for a competition."""
        result = q.competition_seasons(_ensure_loader(loader), competition)
        return json.dumps(result, ensure_ascii=False, default=str)

    @mcp.tool()
    def average_goals(
        competition: Optional[str] = None,
        season: Optional[int] = None,
    ) -> str:
        """Compute average goals per match and home win rate."""
        result = q.average_goals(_ensure_loader(loader), competition, season)
        return json.dumps(result, ensure_ascii=False, default=str)

    @mcp.tool()
    def biggest_wins(
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> str:
        """Return the largest victory margins in the dataset."""
        result = q.biggest_wins(_ensure_loader(loader), competition, season, limit)
        return json.dumps(result, ensure_ascii=False, default=str)

    @mcp.tool()
    def home_vs_away_record(team: str, season: Optional[int] = None) -> str:
        """Split a team's record into home and away portions."""
        result = q.home_vs_away_record(_ensure_loader(loader), team, season)
        return json.dumps(result, ensure_ascii=False, default=str)

    @mcp.tool()
    def last_match_between(team_a: str, team_b: str) -> str:
        """Return the most recent match between two teams."""
        result = q.last_match_between(_ensure_loader(loader), team_a, team_b)
        return json.dumps(result, ensure_ascii=False, default=str)

    return mcp


def main() -> None:
    """Entry point for the console script."""
    create_server().run()


if __name__ == "__main__":
    main()
