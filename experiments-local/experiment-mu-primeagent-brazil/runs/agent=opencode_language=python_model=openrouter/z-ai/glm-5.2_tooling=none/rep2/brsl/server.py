"""MCP server exposing the Brazilian Soccer query engine as MCP tools.

The server uses the official ``mcp`` v2 SDK. Each public query from
:mod:`brsl.query_engine.QueryEngine` is wrapped as an MCP tool whose arguments
are described by a plain function signature (the SDK derives the JSON schema
from the type annotations). The server runs over stdio by default, which is the
transport MCP clients use to launch a subprocess server.
"""
from __future__ import annotations

import json
from typing import Any

from mcp.server.mcpserver import MCPServer

from .query_engine import QueryEngine, get_engine


def _tool_result(payload: Any) -> str:
    """Serialise a query result as JSON text content for the MCP response."""
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)


def build_server(engine: QueryEngine | None = None) -> MCPServer:
    """Build and return the :class:`MCPServer` with all tools registered."""
    engine = engine or get_engine()
    server = MCPServer(
        name="brazilian-soccer-mcp",
        version="0.2.0",
        instructions=(
            "Knowledge graph of Brazilian soccer. Ask about matches, teams, "
            "players, competitions (Brasileirao, Copa do Brasil, Libertadores) "
            "and statistics. Team names may use state suffixes "
            "(e.g. 'Atletico-MG') or accents.")
    )

    # ----- Match queries --------------------------------------------------
    @server.tool(name="search_matches",
                 description=("Search matches by team, opponent, competition, "
                              "season and/or date range."))
    def search_matches(team: str | None = None,
                       opponent: str | None = None,
                       competition: str | None = None,
                       season: int | None = None,
                       date_from: str | None = None,
                       date_to: str | None = None,
                       limit: int = 50) -> str:
        return _tool_result(engine.search_matches(
            team=team, opponent=opponent, competition=competition, season=season,
            date_from=date_from, date_to=date_to, limit=limit))

    @server.tool(name="head_to_head",
                 description=("Compare two teams head-to-head across all "
                              "matches in the dataset."))
    def head_to_head(team_a: str, team_b: str,
                     competition: str | None = None) -> str:
        return _tool_result(engine.head_to_head(team_a, team_b, competition))

    # ----- Team queries ---------------------------------------------------
    @server.tool(name="team_stats",
                 description=("Return win/draw/loss/goals statistics for a "
                              "team, optionally filtered by season, competition "
                              "and venue ('home'|'away')."))
    def team_stats(team: str, season: int | None = None,
                   competition: str | None = None,
                   venue: str | None = None) -> str:
        return _tool_result(engine.team_stats(team, season=season,
                                              competition=competition,
                                              venue=venue))

    @server.tool(name="team_competitions",
                 description="List all competitions a team has played in.")
    def team_competitions(team: str) -> str:
        return _tool_result(engine.team_competitions(team))

    @server.tool(name="team_summary",
                 description=("Cross-file summary of a team: match stats, "
                              "competitions and FIFA player roster."))
    def team_summary(team: str) -> str:
        return _tool_result(engine.team_summary(team))

    # ----- Player queries -------------------------------------------------
    @server.tool(name="search_players",
                 description=("Search FIFA players by name, nationality, club, "
                              "position and minimum overall rating."))
    def search_players(name: str | None = None,
                       nationality: str | None = None,
                       club: str | None = None,
                       position: str | None = None,
                       min_overall: int | None = None,
                       order_by: str = "Overall",
                       limit: int = 20) -> str:
        return _tool_result(engine.search_players(
            name=name, nationality=nationality, club=club, position=position,
            min_overall=min_overall, order_by=order_by, limit=limit))

    @server.tool(name="top_brazilian_players",
                 description="Top-rated Brazilian players in the FIFA dataset.")
    def top_brazilian_players(limit: int = 10) -> str:
        return _tool_result(engine.top_brazilian_players(limit=limit))

    @server.tool(name="players_at_brazilian_clubs",
                 description=("Brazilian players grouped by Brazilian club with "
                              "average ratings."))
    def players_at_brazilian_clubs(limit: int = 10) -> str:
        return _tool_result(engine.players_at_brazilian_clubs(limit=limit))

    @server.tool(name="team_players",
                 description="FIFA players whose club matches a team name.")
    def team_players(team: str, limit: int = 50) -> str:
        return _tool_result(engine.team_players(team, limit=limit))

    # ----- Competition queries -------------------------------------------
    @server.tool(name="standings",
                 description=("Compute a league standings table (3 pts win, "
                              "1 draw) for a competition and season. "
                              "Champion is flagged."))
    def standings(competition: str, season: int, limit: int | None = None) -> str:
        return _tool_result(engine.standings(competition, season, limit=limit))

    @server.tool(name="champion",
                 description="Return the champion team of a league season.")
    def champion(competition: str, season: int) -> str:
        return _tool_result(engine.champion(competition, season))

    @server.tool(name="relegated",
                 description="Return the bottom n teams of a league season.")
    def relegated(competition: str, season: int, n: int = 4) -> str:
        return _tool_result(engine.relegated(competition, season, n=n))

    @server.tool(name="cup_bracket",
                 description=("Return cup (Copa do Brasil / Libertadores) "
                              "matches grouped by round or stage."))
    def cup_bracket(competition: str, season: int) -> str:
        return _tool_result(engine.cup_bracket(competition, season))

    # ----- Statistical analysis ------------------------------------------
    @server.tool(name="average_goals",
                 description=("Average goals per match plus home/draw/away win "
                              "rates for a competition and/or season."))
    def average_goals(competition: str | None = None,
                      season: int | None = None) -> str:
        return _tool_result(engine.average_goals(competition, season))

    @server.tool(name="home_vs_away",
                 description="Home vs away performance breakdown.")
    def home_vs_away(competition: str | None = None,
                     season: int | None = None) -> str:
        return _tool_result(engine.home_vs_away(competition, season))

    @server.tool(name="biggest_victories",
                 description="Largest victory margins in the dataset.")
    def biggest_victories(competition: str | None = None,
                          season: int | None = None,
                          limit: int = 10) -> str:
        return _tool_result(engine.biggest_victories(
            competition, season, limit=limit))

    @server.tool(name="top_scoring_teams",
                 description="Teams ranked by total goals scored.")
    def top_scoring_teams(season: int | None = None,
                          competition: str | None = None,
                          limit: int = 10) -> str:
        return _tool_result(engine.top_scoring_teams(
            season=season, competition=competition, limit=limit))

    @server.tool(name="derbies",
                 description=("Find matches between traditional Brazilian rival "
                              "pairs (Fla-Flu, Majestoso, GreNal, ...)."))
    def derbies(season: int | None = None, limit: int = 50) -> str:
        return _tool_result(engine.derbies(season=season, limit=limit))

    return server


def main() -> None:
    """Entry point: build the server and run it over stdio."""
    build_server().run(transport="stdio")


if __name__ == "__main__":
    main()
