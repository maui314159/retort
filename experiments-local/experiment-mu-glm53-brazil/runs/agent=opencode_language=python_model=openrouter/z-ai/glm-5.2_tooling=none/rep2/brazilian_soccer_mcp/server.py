# SPDX-License-Identifier: Apache-2.0
# Context block ----------------------------------------------------------------
# Module: brazilian_soccer_mcp.server
# Purpose: MCP server exposing the Brazilian soccer query engine as tools.
#
# Uses the Model Context Protocol Python SDK v2 (mcp>=2.1, MCPServer).
# Transport: stdio (the canonical local-tool transport for MCP). Each tool
# is a thin wrapper around a QueryEngine method so the wire payload is plain
# JSON-serializable dicts/lists.
#
# Tools exposed (mirrors the 5 capability categories in the spec):
#   search_matches, head_to_head, team_statistics, competitions_for_team,
#   search_players, top_rated_by_nationality, top_rated_by_club,
#   list_competitions, standings, average_goals, biggest_wins,
#   best_record_by_venue, top_scorers_by_team, derbies_in_season,
#   list_teams, list_sources
#
# Run as:  python -m brazilian_soccer_mcp.server
# Or via the console_script: brazilian-soccer-mcp
# --------------------------------------------------------------------------- #
"""MCP server entry point for the Brazilian soccer knowledge graph."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from brazilian_soccer_mcp.data_loader import DataLoader
from brazilian_soccer_mcp.queries import QueryEngine


def _json_default(obj: Any) -> Any:
    """Fallback serializer for non-JSON-native types (date, datetime, set)."""
    import datetime as _dt
    if isinstance(obj, (_dt.date, _dt.datetime)):
        return obj.isoformat()
    if isinstance(obj, set):
        return sorted(obj)
    raise TypeError(f"not JSON serializable: {type(obj)}")


def _to_jsonable(obj: Any) -> Any:
    """Round-trip through JSON so MCP sees only primitive types."""
    return json.loads(json.dumps(obj, default=_json_default))


def _to_json_str(obj: Any) -> str:
    """Serialize a query result to a JSON string for MCP text content."""
    return json.dumps(obj, default=_json_default, ensure_ascii=False)


class BrazilianSoccerServer:
    """Thin wrapper that registers QueryEngine methods as MCP tools."""

    def __init__(self, data_dir: str | None = None) -> None:
        loader = DataLoader(data_dir) if data_dir else DataLoader()
        loader.load_all()
        self.engine = QueryEngine(loader)

    def build(self):
        """Build and return a configured MCPServer instance."""
        from mcp.server.mcpserver import MCPServer

        server = MCPServer(
            name="brazilian-soccer-mcp",
            version="1.0.0",
            instructions=(
                "Brazilian soccer knowledge graph. Query matches, teams, "
                "players, competitions, and statistics across Brasileirão, "
                "Copa do Brasil, Copa Libertadores, historical Brasileirão "
                "(2003-2019), the extended football stats dataset, and the "
                "FIFA player database. Team names may be supplied in any "
                "spelling; they are canonicalized automatically."
            ),
        )
        engine = self.engine

        @server.tool(
            name="search_matches",
            description=(
                "Find matches by team, opponent, competition, season, and/or "
                "date range. Returns the most recent matching matches first. "
                "Pass team (any spelling); optionally opponent, competition "
                "(substring, accent-insensitive), season (YYYY), "
                "start_date/end_date (YYYY-MM-DD)."
            ),
        )
        def search_matches(
            team: str | None = None,
            opponent: str | None = None,
            competition: str | None = None,
            season: int | None = None,
            start_date: str | None = None,
            end_date: str | None = None,
            limit: int = 100,
        ) -> str:
            return _to_json_str(engine.search_matches(
                team=team, opponent=opponent, competition=competition,
                season=season, start_date=start_date, end_date=end_date,
                limit=limit,
            ))

        @server.tool(
            name="head_to_head",
            description=(
                "Head-to-head record between two teams. Pass team_a and team_b "
                "(any spelling). Returns wins/draws/goals and the list of "
                "matches between them."
            ),
        )
        def head_to_head(
            team_a: str, team_b: str, competition: str | None = None
        ) -> str:
            return _to_json_str(engine.head_to_head(team_a, team_b, competition))

        @server.tool(
            name="team_statistics",
            description=(
                "Aggregate win/draw/loss/goal record for a team. Optional "
                "filters: season (YYYY), competition (substring), venue "
                "('home' or 'away')."
            ),
        )
        def team_statistics(
            team: str,
            season: int | None = None,
            competition: str | None = None,
            venue: str | None = None,
        ) -> str:
            return _to_json_str(engine.team_statistics(
                team=team, season=season, competition=competition, venue=venue
            ))

        @server.tool(
            name="competitions_for_team",
            description=(
                "List the competitions a team has played in, with match counts."
            ),
        )
        def competitions_for_team(team: str) -> str:
            return _to_json_str(engine.competitions_for_team(team))

        @server.tool(
            name="search_players",
            description=(
                "Search FIFA player data by name, nationality, club, "
                "position, and/or minimum overall rating. Sorted by overall "
                "rating (descending) by default."
            ),
        )
        def search_players(
            name: str | None = None,
            nationality: str | None = None,
            club: str | None = None,
            position: str | None = None,
            min_overall: int | None = None,
            limit: int = 50,
        ) -> str:
            return _to_json_str(engine.search_players(
                name=name, nationality=nationality, club=club,
                position=position, min_overall=min_overall, limit=limit
            ))

        @server.tool(
            name="top_rated_by_nationality",
            description=(
                "Top-rated FIFA players for a nationality (e.g. 'Brazil')."
            ),
        )
        def top_rated_by_nationality(nationality: str, limit: int = 10) -> str:
            return _to_json_str(engine.top_rated_by_nationality(nationality, limit))

        @server.tool(
            name="top_rated_by_club",
            description="Top-rated FIFA players at a given club (any spelling)."
        )
        def top_rated_by_club(club: str, limit: int = 10) -> str:
            return _to_json_str(engine.top_rated_by_club(club, limit))

        @server.tool(
            name="list_competitions",
            description="List competitions present in the data with match and "
                        "season counts.",
        )
        def list_competitions() -> str:
            return _to_json_str(engine.list_competitions())

        @server.tool(
            name="standings",
            description=(
                "Calculated league standings for a season. Pass season (YYYY) "
                "and competition (default 'Brasileirão Série A'). Cup "
                "competitions return a note explaining they are knockouts."
            ),
        )
        def standings(season: int, competition: str = "Brasileirão Série A") -> str:
            return _to_json_str(engine.standings(season, competition))

        @server.tool(
            name="average_goals",
            description=(
                "Average goals per match and home/away/draw win rates. "
                "Optional competition and season filters."
            ),
        )
        def average_goals(
            competition: str | None = None, season: int | None = None
        ) -> str:
            return _to_json_str(engine.average_goals(competition, season))

        @server.tool(
            name="biggest_wins",
            description=(
                "Matches with the largest goal margins (victories). Optional "
                "competition and season filters."
            ),
        )
        def biggest_wins(
            competition: str | None = None,
            season: int | None = None,
            limit: int = 10,
        ) -> str:
            return _to_json_str(engine.biggest_wins(competition, season, limit))

        @server.tool(
            name="best_record_by_venue",
            description=(
                "Teams with the best win rate at 'home' or 'away'. Optional "
                "competition filter; min_matches default 10."
            ),
        )
        def best_record_by_venue(
            venue: str,
            competition: str | None = None,
            min_matches: int = 10,
        ) -> str:
            return _to_json_str(engine.best_record_by_venue(
                venue, competition, min_matches
            ))

        @server.tool(
            name="top_scorers_by_team",
            description=(
                "Proxy for a team's top goal threats using the FIFA "
                "'Finishing' attribute (the match CSVs do not name scorers)."
            ),
        )
        def top_scorers_by_team(team: str, limit: int = 10) -> str:
            return _to_json_str(engine.top_scorers_by_team(team, limit))

        @server.tool(
            name="derbies_in_season",
            description="All traditional derby matches in a given season (YYYY).",
        )
        def derbies_in_season(season: int) -> str:
            return _to_json_str(engine.derbies_in_season(season))

        @server.tool(
            name="list_teams",
            description="List all canonical team keys + display names, "
                        "optionally filtered by competition.",
        )
        def list_teams(competition: str | None = None) -> str:
            return _to_json_str(engine.list_teams(competition))

        @server.tool(
            name="list_sources",
            description="Summary of the loaded Kaggle datasets (counts).",
        )
        def list_sources() -> str:
            return _to_json_str(engine.sources())

        return server


def main() -> None:
    """Console-script entry point: run the MCP server over stdio."""
    data_dir = os.environ.get("BRAZILIAN_SOCCER_DATA_DIR")
    srv = BrazilianSoccerServer(data_dir=data_dir).build()
    asyncio.run(srv.run_stdio_async())


if __name__ == "__main__":
    main()
