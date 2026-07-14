# ============================================================================
# Context: Brazilian Soccer MCP Server benchmark.
# FastMCP server. Registers the QueryEngine methods as MCP tools so an LLM
# client can invoke them over the Model Context Protocol. The server can be
# launched with `python -m brazilian_soccer_mcp.server` or the
# `brazilian-soccer-mcp` console script and speaks stdio by default.
# ----------------------------------------------------------------------------
from __future__ import annotations

from typing import Optional

from fastmcp import FastMCP

from .data_loader import DataLoader
from .queries import QueryEngine


def build_server(loader: Optional[DataLoader] = None) -> FastMCP:
    """Construct a FastMCP server with all Brazilian-soccer tools registered."""
    engine = QueryEngine(loader or DataLoader())
    mcp = FastMCP("brazilian-soccer-mcp")

    @mcp.tool
    def find_matches(
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[dict]:
        """Find matches by team, opponent, competition, season, and/or date range.

        Team and opponent match either side of the match. Dates are ISO
        (YYYY-MM-DD). Returns newest-first list of match summaries.
        """
        return engine.find_matches(
            team=team, opponent=opponent, competition=competition,
            season=season, start_date=start_date, end_date=end_date, limit=limit,
        )

    @mcp.tool
    def head_to_head(team_a: str, team_b: str) -> dict:
        """Head-to-head record between two teams across all datasets."""
        return engine.head_to_head(team_a, team_b)

    @mcp.tool
    def team_stats(
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        venue: Optional[str] = None,
    ) -> dict:
        """Win/loss/draw and goal aggregates for a team. venue is 'home' or 'away'."""
        return engine.team_stats(team, season=season, competition=competition, venue=venue)

    @mcp.tool
    def search_players(
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> list[dict]:
        """Search the FIFA player database by name, nationality, club, position, rating."""
        return engine.search_players(
            name=name, nationality=nationality, club=club,
            position=position, min_overall=min_overall, limit=limit,
        )

    @mcp.tool
    def top_brazilian_players(limit: int = 20) -> list[dict]:
        """Highest-rated Brazilian players in the FIFA dataset."""
        return engine.top_brazilian_players(limit=limit)

    @mcp.tool
    def players_at_club(club: str, limit: Optional[int] = None) -> list[dict]:
        """All FIFA players whose club matches the given team name."""
        return engine.players_at_club(club, limit=limit)

    @mcp.tool
    def standings(competition: str, season: int) -> list[dict]:
        """Calculated league standings (points table) for a competition/season."""
        return engine.standings(competition, season)

    @mcp.tool
    def champion(competition: str, season: int) -> Optional[dict]:
        """Return the champion (top of standings) for a competition/season."""
        return engine.champion(competition, season)

    @mcp.tool
    def relegated_teams(competition: str, season: int, n: int = 4) -> list[dict]:
        """Return the bottom n teams in the standings (relegation zone)."""
        return engine.relegated_teams(competition, season, n=n)

    @mcp.tool
    def average_goals(
        competition: Optional[str] = None,
        season: Optional[int] = None,
    ) -> dict:
        """Average goals per match plus home/away win rates."""
        return engine.average_goals(competition=competition, season=season)

    @mcp.tool
    def biggest_wins(
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> list[dict]:
        """Largest goal-margin victories in the dataset."""
        return engine.biggest_wins(competition=competition, season=season, limit=limit)

    @mcp.tool
    def best_home_record(
        season: Optional[int] = None,
        competition: Optional[str] = None,
    ) -> Optional[dict]:
        """Team with the highest home win rate (min 5 matches)."""
        return engine.best_home_record(season=season, competition=competition)

    @mcp.tool
    def best_away_record(
        season: Optional[int] = None,
        competition: Optional[str] = None,
    ) -> Optional[dict]:
        """Team with the highest away win rate (min 5 matches)."""
        return engine.best_away_record(season=season, competition=competition)

    @mcp.tool
    def list_teams(competition: Optional[str] = None) -> list[str]:
        """Sorted unique team names, optionally filtered by competition."""
        return engine.list_teams(competition=competition)

    @mcp.tool
    def list_competitions() -> list[str]:
        """Distinct competition labels present in the dataset."""
        return engine.list_competitions()

    @mcp.tool
    def list_seasons(competition: Optional[str] = None) -> list[int]:
        """Sorted distinct seasons available, optionally per competition."""
        return engine.list_seasons(competition=competition)

    return mcp


def main() -> None:
    """Entry point: build the server and run it over stdio."""
    build_server().run()


if __name__ == "__main__":
    main()
