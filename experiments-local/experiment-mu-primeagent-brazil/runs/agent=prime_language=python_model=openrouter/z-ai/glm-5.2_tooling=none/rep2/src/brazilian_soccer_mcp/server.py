"""
Context block
=============
Brazilian Soccer MCP Server - MCP Tool Layer
---------------------------------------------
Purpose: Expose the QueryEngine capabilities as MCP (Model Context Protocol)
tools so an LLM client can answer natural-language questions about Brazilian
soccer using the six provided datasets.

This module:
  * Builds an `MCPServer` (mcp v2) and registers one tool per QueryEngine
    capability. Each tool is a thin, type-annotated wrapper that returns a
    JSON string of the underlying engine result.
  * Keeps the tool functions importable at module level (`tool_*`) so they can
    be unit-tested directly without spawning a subprocess.
  * Provides `main()` to run the server over stdio for real MCP integration.

Run with:  python -m brazilian_soccer_mcp.server   (stdio transport)
"""

from __future__ import annotations

import json

from mcp.server.mcpserver import MCPServer

from .queries import QueryEngine, get_engine

_server: MCPServer | None = None


def _eng() -> QueryEngine:
    return get_engine()


def _dump(obj) -> str:
    """Serialize an engine result to a JSON string (UTF-8 friendly)."""
    return json.dumps(obj, ensure_ascii=False, default=str)


# ----------------------------------------------------------------- tool fns
def tool_find_matches(team: str | None = None,
                      opponent: str | None = None,
                      competition: str | None = None,
                      season: int | None = None,
                      start_date: str | None = None,
                      end_date: str | None = None,
                      limit: int = 100) -> str:
    """Find matches by team, opponent, competition, season and/or date range."""
    return _dump(_eng().find_matches(
        team=team, opponent=opponent, competition=competition, season=season,
        start_date=start_date, end_date=end_date, limit=limit))


def tool_head_to_head(team_a: str, team_b: str,
                      competition: str | None = None) -> str:
    """Head-to-head record between two teams."""
    return _dump(_eng().head_to_head(team_a, team_b, competition=competition))


def tool_last_match_between(team_a: str, team_b: str) -> str:
    """Most recent match played between two teams."""
    return _dump(_eng().last_match_between(team_a, team_b))


def tool_team_statistics(team: str,
                          season: int | None = None,
                          competition: str | None = None,
                          venue: str | None = None) -> str:
    """Win/draw/loss and goal stats for a team (optionally by season/venue)."""
    return _dump(_eng().team_statistics(
        team=team, season=season, competition=competition, venue=venue))


def tool_team_competitions(team: str) -> str:
    """List competitions a team has appeared in with match counts."""
    return _dump(_eng().team_competitions(team))


def tool_search_players(name: str | None = None,
                        nationality: str | None = None,
                        club: str | None = None,
                        position: str | None = None,
                        min_rating: int | None = None,
                        limit: int = 50) -> str:
    """Search FIFA players by name/nationality/club/position/rating."""
    return _dump(_eng().search_players(
        name=name, nationality=nationality, club=club, position=position,
        min_rating=min_rating, limit=limit))


def tool_top_brazilian_players(limit: int = 20) -> str:
    """Top-rated Brazilian players in the FIFA dataset."""
    return _dump(_eng().top_brazilian_players(limit=limit))


def tool_players_at_club(club: str) -> str:
    """All FIFA players at a given club (highest-rated first)."""
    return _dump(_eng().players_at_club(club))


def tool_brazilian_players_by_club() -> str:
    """Count of Brazilian players per Brazilian club with average rating."""
    return _dump(_eng().brazilian_players_by_club())


def tool_standings(competition: str = "brasileirao",
                   season: int | None = None,
                   top: int | None = None) -> str:
    """League standings calculated from match results (3 pts/win)."""
    return _dump(_eng().standings(competition=competition, season=season, top=top))


def tool_biggest_wins(competition: str | None = None, limit: int = 10) -> str:
    """Biggest victories by goal margin in the dataset."""
    return _dump(_eng().biggest_wins(competition=competition, limit=limit))


def tool_average_goals(competition: str | None = None,
                       season: int | None = None) -> str:
    """Average goals per match and home/away win/draw rates."""
    return _dump(_eng().average_goals(competition=competition, season=season))


def tool_best_home_record(competition: str = "brasileirao",
                          season: int | None = None,
                          top: int = 10) -> str:
    """Teams with the best home win rate."""
    return _dump(_eng().best_home_record(
        competition=competition, season=season, top=top))


def tool_best_away_record(competition: str = "brasileirao",
                          season: int | None = None,
                          top: int = 10) -> str:
    """Teams with the best away win rate (min 10 away matches)."""
    return _dump(_eng().best_away_record(
        competition=competition, season=season, top=top))


def tool_derbies(competition: str | None = None,
                 season: int | None = None,
                 limit: int = 100) -> str:
    """Traditional Brazilian derby matches (Fla-Flu, Gre-Nal, Majestoso...)."""
    return _dump(_eng().derbies(competition=competition, season=season, limit=limit))


def tool_seasons_summary(competition: str = "brasileirao") -> str:
    """Per-season aggregate summary for a competition."""
    return _dump(_eng().seasons_summary(competition=competition))


# Mapping of tool name -> (callable, description) for inspection/testing.
TOOL_REGISTRY = [
    ("find_matches", tool_find_matches,
     "Find matches by team, opponent, competition, season and/or date range."),
    ("head_to_head", tool_head_to_head,
     "Head-to-head record between two teams."),
    ("last_match_between", tool_last_match_between,
     "Most recent match played between two teams."),
    ("team_statistics", tool_team_statistics,
     "Win/draw/loss and goal stats for a team."),
    ("team_competitions", tool_team_competitions,
     "List competitions a team has appeared in."),
    ("search_players", tool_search_players,
     "Search FIFA players by name/nationality/club/position/rating."),
    ("top_brazilian_players", tool_top_brazilian_players,
     "Top-rated Brazilian players in the FIFA dataset."),
    ("players_at_club", tool_players_at_club,
     "All FIFA players at a given club."),
    ("brazilian_players_by_club", tool_brazilian_players_by_club,
     "Count of Brazilian players per Brazilian club with avg rating."),
    ("standings", tool_standings,
     "League standings calculated from match results."),
    ("biggest_wins", tool_biggest_wins,
     "Biggest victories by goal margin in the dataset."),
    ("average_goals", tool_average_goals,
     "Average goals per match and home/away win/draw rates."),
    ("best_home_record", tool_best_home_record,
     "Teams with the best home win rate."),
    ("best_away_record", tool_best_away_record,
     "Teams with the best away win rate."),
    ("derbies", tool_derbies,
     "Traditional Brazilian derby matches."),
    ("seasons_summary", tool_seasons_summary,
     "Per-season aggregate summary for a competition."),
]


def create_server() -> MCPServer:
    """Build and return the MCPServer with all tools registered."""
    global _server
    server = MCPServer(
        name="brazilian-soccer-mcp",
        title="Brazilian Soccer MCP Server",
        description=(
            "Knowledge-graph style MCP server exposing Brazilian soccer match, "
            "team, player and competition data from the provided Kaggle "
            "datasets."
        ),
        instructions=(
            "Use these tools to answer natural language questions about "
            "Brazilian soccer: matches, teams, players, competitions and "
            "statistics. Team names are normalized across datasets so e.g. "
            "'Flamengo', 'Flamengo-RJ' and 'Flamengo - RJ' all match."
        ),
        version="2.0",
    )
    for name, fn, desc in TOOL_REGISTRY:
        server.add_tool(fn, name=name, description=desc)
    _server = server
    return server


def list_tool_names() -> list[str]:
    """Return the names of all registered MCP tools."""
    return [name for name, _, _ in TOOL_REGISTRY]


def main() -> None:
    """Run the MCP server over stdio (for real MCP clients)."""
    server = create_server()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
