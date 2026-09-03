"""
Context
=======
Brazilian Soccer MCP Server - MCP protocol layer.

Part of the ``soccer_mcp`` package.  Wraps the query functions in
:mod:`soccer_mcp.queries` as MCP tools so an LLM client (Claude / any MCP-aware
model) can answer natural-language questions about Brazilian soccer by calling
tools such as ``find_matches``, ``head_to_head``, ``team_stats``,
``search_players``, ``standings``, ``champion``, ``statistics`` and
``biggest_wins``.

Compatibility
-------------
The official ``mcp`` Python SDK renamed ``FastMCP`` to ``MCPServer`` in v2.0
(``from mcp.server.mcpserver import MCPServer``) while keeping the same
``@server.tool()`` decorator and ``server.run()`` API.  This module imports the
new class first and falls back to the v1 ``FastMCP`` so the server runs with
either ``mcp>=2`` or ``mcp<2``.

Design
------
* ``build_server()`` constructs and returns a configured MCP server with every
  tool registered.  It is called lazily so that importing this module (e.g. in
  tests) does not require ``mcp`` to be installed.
* Each tool delegates to a pure function in :mod:`soccer_mcp.queries` and
  returns JSON-serialisable dicts/lists.  ``ValueError`` raised by the query
  layer (e.g. standings for a cup competition) is caught and returned as an
  ``{"error": ...}`` dict so the MCP session never crashes.
* The server is runnable directly with ``python server.py`` (project root) or
  ``python -m soccer_mcp.server``.
"""

from __future__ import annotations

from typing import Optional

from . import queries

# Import the MCP server class with a v1/v2 compatibility shim.
try:  # mcp >= 2.0
    from mcp.server.mcpserver import MCPServer as _McpServer
except ImportError:  # pragma: no cover - fallback for mcp < 2.0
    from mcp.server.fastmcp import FastMCP as _McpServer  # type: ignore

SERVER_NAME = "brazilian-soccer-mcp"
SERVER_VERSION = "1.0.0"


def build_server():  # -> MCPServer / FastMCP
    """Build and return the MCP server with all tools registered."""
    server = _McpServer(SERVER_NAME)

    @server.tool()
    def list_competitions() -> list[dict]:
        """List every competition available in the dataset with seasons, match
        counts and number of teams."""
        return queries.list_competitions()

    @server.tool()
    def list_teams(
        competition: Optional[str] = None,
        season: Optional[str] = None,
    ) -> list[str]:
        """List team display names, optionally filtered by competition and/or
        season. Use this to resolve team name variations before deeper
        queries (e.g. 'Palmeiras', 'Palmeiras-SP' all map to Palmeiras)."""
        return queries.list_teams(competition=competition, season=season)

    @server.tool()
    def find_matches(
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        stage: Optional[str] = None,
        venue: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """Find matches matching criteria. ``venue`` is 'home'/'away'/'either'
        for ``team``. Dates are ISO YYYY-MM-DD and inclusive. ``competition``
        accepts aliases like 'brasileirao', 'serie a', 'copa do brasil',
        'libertadores'. Returns date, score, competition and source per match.
        Examples: 'Flamengo vs Fluminense matches', 'Palmeiras in 2023',
        'Copa do Brasil finals' (use stage='final' for the latter)."""
        return queries.find_matches(
            team=team, opponent=opponent, competition=competition, season=season,
            date_from=date_from, date_to=date_to, stage=stage, venue=venue,
            limit=limit,
        )

    @server.tool()
    def head_to_head(
        team_a: str,
        team_b: str,
        competition: Optional[str] = None,
        limit: int = 100,
    ) -> dict:
        """Head-to-head record between two teams: wins, draws, goals and the
        list of matches between them across all competitions (or one)."""
        return queries.head_to_head(team_a, team_b, competition=competition, limit=limit)

    @server.tool()
    def team_stats(
        team: str,
        season: Optional[str] = None,
        competition: Optional[str] = None,
        venue: Optional[str] = None,
    ) -> dict:
        """Win/draw/loss and goal record for a team, overall plus split by home
        and away and by competition. Filter by season and/or competition and/or
        venue ('home'/'away')."""
        return queries.team_stats(team, season=season, competition=competition, venue=venue)

    @server.tool()
    def search_players(
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: int = 0,
        max_overall: Optional[int] = None,
        limit: int = 25,
        sort_by_overall: bool = True,
    ) -> list[dict]:
        """Search the FIFA player database by name substring, nationality,
        club, position code (ST, LW, CDM, GK...), and overall rating range.
        Sort by overall by default. Examples: Brazilian players, top-rated at a
        club, forwards from a team. ``club`` matches FIFA club text OR the
        canonical soccer-team key (cross-file)."""
        return queries.search_players(
            name=name, nationality=nationality, club=club, position=position,
            min_overall=min_overall, max_overall=max_overall, limit=limit,
            sort_by_overall=sort_by_overall,
        )

    @server.tool()
    def team_players(
        team: str,
        position: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """FIFA players whose club matches a soccer team (cross-file query).
        Useful for 'which players play for Flamengo?' style questions."""
        return queries.team_players(team, position=position, limit=limit)

    @server.tool()
    def standings(
        competition: str,
        season: str,
        top: Optional[int] = None,
    ) -> list[dict]:
        """Calculated league standings (points, W/D/L, goals, goal difference)
        for Brasileirao Serie A/B/C. Not supported for cup competitions.
        Returns an error dict for unknown competitions/seasons."""
        try:
            return queries.standings(competition, season, top=top)
        except ValueError as exc:
            return [{"error": str(exc)}]

    @server.tool()
    def champion(competition: str, season: str) -> dict:
        """Return the champion (top of the calculated standings) for a league
        competition and season, e.g. 'Who won the 2019 Brasileirao?'."""
        try:
            return queries.champion(competition, season)
        except ValueError as exc:
            return {"error": str(exc)}

    @server.tool()
    def relegated(competition: str, season: str, n: int = 4) -> list[dict]:
        """Bottom ``n`` (default 4) teams of a league standings table, e.g.
        'Which teams were relegated in 2020?'."""
        try:
            return queries.relegated(competition, season, n=n)
        except ValueError as exc:
            return [{"error": str(exc)}]

    @server.tool()
    def statistics(
        competition: Optional[str] = None,
        season: Optional[str] = None,
    ) -> dict:
        """Aggregate goal/result statistics: average goals per match, home vs
        away win rates, draw rate, average home/away goals. Optionally filter
        by competition and/or season."""
        return queries.statistics(competition=competition, season=season)

    @server.tool()
    def biggest_wins(
        competition: Optional[str] = None,
        season: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict]:
        """Largest victory margins in the dataset, optionally filtered by
        competition/season."""
        return queries.biggest_wins(competition=competition, season=season, limit=limit)

    @server.tool()
    def match_stats(
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[str] = None,
        limit: int = 25,
    ) -> list[dict]:
        """Detailed per-match statistics (corners, shots, attacks, half-time
        result) from the BR-Football-Dataset for matches matching the
        criteria."""
        return queries.match_stats(
            team=team, opponent=opponent, competition=competition,
            season=season, limit=limit,
        )

    return server


def main() -> None:
    """Entry point: build the server and run it over stdio."""
    server = build_server()
    server.run("stdio")


if __name__ == "__main__":
    main()
