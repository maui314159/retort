"""
MCP server exposing the Brazilian soccer query API as Model Context Protocol
tools.

Context block
=============
Purpose: Bridge the ``SoccerQueryEngine`` to the Model Context Protocol so an
LLM client can answer natural-language questions about Brazilian soccer. The
server runs over stdio (JSON-RPC 2.0) using the official ``mcp`` Python SDK.

Tools exposed
-------------
- ``find_matches``          : search matches by team/opponent/competition/season/date
- ``head_to_head``          : head-to-head record between two teams
- ``team_stats``            : win/draw/loss + goal stats for a team
- ``compare_teams``         : compare two teams + their head-to-head
- ``find_players``          : search the FIFA player database
- ``top_players_for_club``  : highest-rated players at a club
- ``brazilian_players``     : top Brazilian players
- ``standings``             : calculated standings for a competition/season
- ``competition_info``      : metadata for competitions
- ``champion``              : champion of a competition/season
- ``relegated_teams``       : bottom teams in standings
- ``average_goals``         : average goals & home/away win rates
- ``biggest_wins``          : largest goal-difference victories
- ``best_away_record``      : teams ranked by away win rate
- ``top_scoring_teams``     : teams ranked by goals scored

Run with ``python -m brazilian_soccer_mcp.mcp_server``.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.types import (
    TextContent,
    Tool,
)

from .queries import SoccerQueryEngine


# A single shared engine instance (data loads lazily on first use).
_engine: SoccerQueryEngine | None = None


def get_engine() -> SoccerQueryEngine:
    global _engine
    if _engine is None:
        _engine = SoccerQueryEngine()
    return _engine


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS: list[Tool] = [
    Tool(
        name="find_matches",
        description="Find soccer matches by team, opponent, competition, season and/or date range. "
                    "Team names are normalized (e.g. 'Palmeiras-SP' == 'Palmeiras').",
        inputSchema={
            "type": "object",
            "properties": {
                "team": {"type": "string", "description": "Team name (home, away or either)."},
                "opponent": {"type": "string", "description": "Opponent team name."},
                "competition": {"type": "string", "description": "Competition name or list of names."},
                "season": {"type": "string", "description": "Season year, e.g. '2023'."},
                "date_from": {"type": "string", "description": "ISO date lower bound (YYYY-MM-DD)."},
                "date_to": {"type": "string", "description": "ISO date upper bound (YYYY-MM-DD)."},
                "limit": {"type": "integer", "description": "Maximum matches to return."},
            },
        },
    ),
    Tool(
        name="head_to_head",
        description="Head-to-head record between two teams (wins, draws, goals, match list).",
        inputSchema={
            "type": "object",
            "properties": {
                "team_a": {"type": "string"},
                "team_b": {"type": "string"},
                "competition": {"type": "string"},
            },
            "required": ["team_a", "team_b"],
        },
    ),
    Tool(
        name="team_stats",
        description="Win/draw/loss and goal statistics for a team, optionally filtered by season, competition and venue.",
        inputSchema={
            "type": "object",
            "properties": {
                "team": {"type": "string"},
                "season": {"type": "string"},
                "competition": {"type": "string"},
                "venue": {"type": "string", "enum": ["home", "away"]},
            },
            "required": ["team"],
        },
    ),
    Tool(
        name="compare_teams",
        description="Compare two teams' statistics and their head-to-head record.",
        inputSchema={
            "type": "object",
            "properties": {
                "team_a": {"type": "string"},
                "team_b": {"type": "string"},
                "season": {"type": "string"},
            },
            "required": ["team_a", "team_b"],
        },
    ),
    Tool(
        name="find_players",
        description="Search the FIFA player database by name, nationality, club, position and/or minimum overall rating.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "nationality": {"type": "string"},
                "club": {"type": "string"},
                "position": {"type": "string"},
                "min_overall": {"type": "integer"},
                "limit": {"type": "integer"},
            },
        },
    ),
    Tool(
        name="top_players_for_club",
        description="Highest-rated players at a given club.",
        inputSchema={
            "type": "object",
            "properties": {
                "club": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["club"],
        },
    ),
    Tool(
        name="brazilian_players",
        description="Top Brazilian players sorted by FIFA overall rating.",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer"},
                "min_overall": {"type": "integer"},
            },
        },
    ),
    Tool(
        name="standings",
        description="Calculate standings for a competition and season from match results (3 pts/win).",
        inputSchema={
            "type": "object",
            "properties": {
                "competition": {"type": "string"},
                "season": {"type": "string"},
            },
            "required": ["competition", "season"],
        },
    ),
    Tool(
        name="competition_info",
        description="Metadata (seasons, match count, teams) for one or all competitions.",
        inputSchema={
            "type": "object",
            "properties": {
                "competition": {"type": "string"},
            },
        },
    ),
    Tool(
        name="champion",
        description="Return the champion (top of standings) for a competition/season.",
        inputSchema={
            "type": "object",
            "properties": {
                "competition": {"type": "string"},
                "season": {"type": "string"},
            },
            "required": ["competition", "season"],
        },
    ),
    Tool(
        name="relegated_teams",
        description="Bottom teams (relegation zone) in a competition/season standings.",
        inputSchema={
            "type": "object",
            "properties": {
                "competition": {"type": "string"},
                "season": {"type": "string"},
                "n": {"type": "integer", "default": 4},
            },
            "required": ["competition", "season"],
        },
    ),
    Tool(
        name="average_goals",
        description="Average goals per match plus home-win/draw/away-win rates.",
        inputSchema={
            "type": "object",
            "properties": {
                "competition": {"type": "string"},
                "season": {"type": "string"},
            },
        },
    ),
    Tool(
        name="biggest_wins",
        description="Largest goal-difference victories in the dataset.",
        inputSchema={
            "type": "object",
            "properties": {
                "competition": {"type": "string"},
                "season": {"type": "string"},
                "limit": {"type": "integer"},
            },
        },
    ),
    Tool(
        name="best_away_record",
        description="Teams ranked by away win rate.",
        inputSchema={
            "type": "object",
            "properties": {
                "competition": {"type": "string"},
                "season": {"type": "string"},
                "limit": {"type": "integer"},
            },
        },
    ),
    Tool(
        name="top_scoring_teams",
        description="Teams ranked by total goals scored.",
        inputSchema={
            "type": "object",
            "properties": {
                "competition": {"type": "string"},
                "season": {"type": "string"},
                "limit": {"type": "integer"},
            },
        },
    ),
]


# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------

def _as_list(value) -> list | None:
    if value is None:
        return None
    if isinstance(value, list):
        return value
    return [value]


def dispatch_tool(name: str, arguments: dict[str, Any]) -> Any:
    """Execute a tool by name and return a JSON-serializable result."""
    engine = get_engine()
    a = arguments or {}

    if name == "find_matches":
        return engine.find_matches(
            team=a.get("team"),
            opponent=a.get("opponent"),
            competition=_as_list(a.get("competition")),
            season=a.get("season"),
            date_from=a.get("date_from"),
            date_to=a.get("date_to"),
            limit=a.get("limit"),
        )
    if name == "head_to_head":
        return engine.head_to_head(
            a["team_a"], a["team_b"], competition=_as_list(a.get("competition"))
        )
    if name == "team_stats":
        return engine.team_stats(
            a["team"], season=a.get("season"),
            competition=_as_list(a.get("competition")), venue=a.get("venue"),
        )
    if name == "compare_teams":
        return engine.compare_teams(a["team_a"], a["team_b"], season=a.get("season"))
    if name == "find_players":
        return engine.find_players(
            name=a.get("name"), nationality=a.get("nationality"),
            club=a.get("club"), position=a.get("position"),
            min_overall=a.get("min_overall"), limit=a.get("limit", 50),
        )
    if name == "top_players_for_club":
        return engine.top_players_for_club(a["club"], limit=a.get("limit", 10))
    if name == "brazilian_players":
        return engine.brazilian_players(limit=a.get("limit", 50), min_overall=a.get("min_overall"))
    if name == "standings":
        return engine.standings(a["competition"], a["season"])
    if name == "competition_info":
        return engine.competition_info(a.get("competition"))
    if name == "champion":
        return engine.champion(a["competition"], a["season"])
    if name == "relegated_teams":
        return engine.relegated_teams(a["competition"], a["season"], n=a.get("n", 4))
    if name == "average_goals":
        return engine.average_goals(competition=_as_list(a.get("competition")), season=a.get("season"))
    if name == "biggest_wins":
        return engine.biggest_wins(
            competition=_as_list(a.get("competition")), season=a.get("season"),
            limit=a.get("limit", 10),
        )
    if name == "best_away_record":
        return engine.best_away_record(
            competition=_as_list(a.get("competition")), season=a.get("season"),
            limit=a.get("limit", 10),
        )
    if name == "top_scoring_teams":
        return engine.top_scoring_teams(
            competition=_as_list(a.get("competition")), season=a.get("season"),
            limit=a.get("limit", 10),
        )
    raise ValueError(f"Unknown tool: {name}")


# ---------------------------------------------------------------------------
# Server bootstrap
# ---------------------------------------------------------------------------

def create_server() -> MCPServer:
    """Build an :class:`MCPServer` registering every query as a callable tool.

    Each tool delegates to :func:`dispatch_tool` and returns a JSON string
    wrapped in a single :class:`TextContent` block, as required by MCP.
    """
    server = MCPServer(
        name="brazilian-soccer-mcp",
        description="Query interface over Brazilian soccer datasets (matches, teams, players).",
    )

    async def _call(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        result = dispatch_tool(name, arguments or {})
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, default=str))]

    # Register every declared tool. ``add_tool`` infers the JSON schema from
    # the wrapper function's signature, so we give each wrapper explicit,
    # annotated parameters mirroring the tool's input schema.
    async def find_matches(team: str | None = None, opponent: str | None = None,
                           competition: str | list[str] | None = None,
                           season: str | None = None, date_from: str | None = None,
                           date_to: str | None = None, limit: int | None = None) -> list[TextContent]:
        """Find soccer matches by team, opponent, competition, season and/or date range."""
        return await _call("find_matches", {k: v for k, v in locals().items() if v is not None})

    async def head_to_head(team_a: str, team_b: str, competition: str | None = None) -> list[TextContent]:
        """Head-to-head record between two teams."""
        return await _call("head_to_head", {k: v for k, v in locals().items() if v is not None})

    async def team_stats(team: str, season: str | None = None,
                         competition: str | list[str] | None = None,
                         venue: str | None = None) -> list[TextContent]:
        """Win/draw/loss and goal statistics for a team."""
        return await _call("team_stats", {k: v for k, v in locals().items() if v is not None})

    async def compare_teams(team_a: str, team_b: str, season: str | None = None) -> list[TextContent]:
        """Compare two teams' statistics and their head-to-head record."""
        return await _call("compare_teams", {k: v for k, v in locals().items() if v is not None})

    async def find_players(name: str | None = None, nationality: str | None = None,
                           club: str | None = None, position: str | None = None,
                           min_overall: int | None = None, limit: int | None = 50) -> list[TextContent]:
        """Search the FIFA player database."""
        return await _call("find_players", {k: v for k, v in locals().items() if v is not None})

    async def top_players_for_club(club: str, limit: int | None = 10) -> list[TextContent]:
        """Highest-rated players at a given club."""
        return await _call("top_players_for_club", {k: v for k, v in locals().items() if v is not None})

    async def brazilian_players(limit: int | None = 50, min_overall: int | None = None) -> list[TextContent]:
        """Top Brazilian players sorted by FIFA overall rating."""
        return await _call("brazilian_players", {k: v for k, v in locals().items() if v is not None})

    async def standings(competition: str, season: str) -> list[TextContent]:
        """Calculate standings for a competition and season from match results."""
        return await _call("standings", {"competition": competition, "season": season})

    async def competition_info(competition: str | None = None) -> list[TextContent]:
        """Metadata for one or all competitions."""
        return await _call("competition_info", {"competition": competition} if competition else {})

    async def champion(competition: str, season: str) -> list[TextContent]:
        """Return the champion for a competition/season."""
        return await _call("champion", {"competition": competition, "season": season})

    async def relegated_teams(competition: str, season: str, n: int | None = 4) -> list[TextContent]:
        """Bottom teams (relegation zone) in a competition/season."""
        return await _call("relegated_teams", {"competition": competition, "season": season, "n": n or 4})

    async def average_goals(competition: str | list[str] | None = None,
                            season: str | None = None) -> list[TextContent]:
        """Average goals per match plus home/draw/away win rates."""
        return await _call("average_goals", {k: v for k, v in locals().items() if v is not None})

    async def biggest_wins(competition: str | list[str] | None = None,
                           season: str | None = None, limit: int | None = 10) -> list[TextContent]:
        """Largest goal-difference victories in the dataset."""
        return await _call("biggest_wins", {k: v for k, v in locals().items() if v is not None})

    async def best_away_record(competition: str | list[str] | None = None,
                               season: str | None = None, limit: int | None = 10) -> list[TextContent]:
        """Teams ranked by away win rate."""
        return await _call("best_away_record", {k: v for k, v in locals().items() if v is not None})

    async def top_scoring_teams(competition: str | list[str] | None = None,
                                season: str | None = None, limit: int | None = 10) -> list[TextContent]:
        """Teams ranked by total goals scored."""
        return await _call("top_scoring_teams", {k: v for k, v in locals().items() if v is not None})

    for fn in (
        find_matches, head_to_head, team_stats, compare_teams, find_players,
        top_players_for_club, brazilian_players, standings, competition_info,
        champion, relegated_teams, average_goals, biggest_wins,
        best_away_record, top_scoring_teams,
    ):
        server.add_tool(fn)

    return server


async def main() -> None:
    server = create_server()
    await server.run_stdio_async()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
