"""Brazilian Soccer MCP Server - MCP tool surface.

Context block
-------------
Purpose: Expose the query/analysis engine as MCP tools that an LLM can
invoke to answer natural-language questions about Brazilian soccer.

Transport: stdio (the default for local MCP servers). Run with:
    python server.py
and point an MCP client (e.g. Claude Desktop) at this script.

Tools exposed (one per spec capability):
  - search_matches            : Match Queries
  - head_to_head              : Match / Team relationship queries
  - team_stats                : Team Queries
  - standings                 : Competition Queries
  - champion                  : Competition Queries
  - relegated_teams           : Competition Queries
  - biggest_wins              : Statistical Analysis
  - average_goals             : Statistical Analysis
  - best_home_record          : Statistical Analysis
  - derbies                   : Relationship Queries
  - search_players            : Player Queries
  - top_brazilian_players     : Player Queries
  - players_at_club           : Player Queries

Why FastMCP: it is the simplest decorator-based API in the `mcp` SDK
(v1 line, pinned via `mcp<2`). Each tool returns JSON-serializable data;
the LLM formats the final natural-language answer.

Test: server logic is covered via analysis.* unit tests; the server
module itself is a thin adapter that delegates to analysis.
"""
from __future__ import annotations

import json
from typing import Optional

from mcp.server.fastmcp import FastMCP

from analysis import (
    avg_goals, best_home_record, biggest_wins, champion, derbies,
    head_to_head, players_at_club, relegated, search_matches,
    search_players, standings, team_stats, top_brazilian_players,
)
from data_loader import SoccerData, get_data

mcp = FastMCP("brazilian-soccer")


def _sd() -> SoccerData:
    return get_data()


@mcp.tool()
def search_matches_tool(
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
) -> str:
    """Find matches by team, opponent, competition, season, and/or date range.

    competition accepts: 'Brasileirão'/'Serie A', 'Copa do Brasil',
    'Libertadores'. Dates are ISO 'YYYY-MM-DD'. Returns JSON match list.
    """
    return json.dumps(search_matches(
        _sd(), team=team, opponent=opponent, competition=competition,
        season=season, start_date=start_date, end_date=end_date, limit=limit,
    ), ensure_ascii=False, indent=2)


@mcp.tool()
def head_to_head_tool(team_a: str, team_b: str) -> str:
    """Compare two teams head-to-head: wins/draws/losses and match list."""
    return json.dumps(head_to_head(_sd(), team_a, team_b), ensure_ascii=False, indent=2)


@mcp.tool()
def team_stats_tool(team: str, season: Optional[int] = None) -> str:
    """Return W/D/L, goals, home/away split for a team, optionally in a season."""
    return json.dumps(team_stats(_sd(), team, season), ensure_ascii=False, indent=2)


@mcp.tool()
def standings_tool(competition: str, season: int) -> str:
    """Compute a league table (standings) for a competition+season."""
    return json.dumps(standings(_sd(), competition, season), ensure_ascii=False, indent=2)


@mcp.tool()
def champion_tool(competition: str, season: int) -> str:
    """Return the champion (top of computed standings) for a competition+season."""
    return json.dumps(champion(_sd(), competition, season), ensure_ascii=False, indent=2)


@mcp.tool()
def relegated_teams_tool(competition: str, season: int, n: int = 4) -> str:
    """Return the bottom n teams (relegated) for a competition+season."""
    return json.dumps(relegated(_sd(), competition, season, n), ensure_ascii=False, indent=2)


@mcp.tool()
def biggest_wins_tool(competition: Optional[str] = None, n: int = 10) -> str:
    """Return the n biggest wins (by goal margin) across all/one competition(s)."""
    return json.dumps(biggest_wins(_sd(), competition=competition, n=n), ensure_ascii=False, indent=2)


@mcp.tool()
def average_goals_tool(competition: Optional[str] = None) -> str:
    """Return average goals/match and home/draw/away win rates."""
    return json.dumps(avg_goals(_sd(), competition=competition), ensure_ascii=False, indent=2)


@mcp.tool()
def best_home_record_tool(
    competition: Optional[str] = None, season: Optional[int] = None, min_matches: int = 5,
) -> str:
    """Rank teams by home win rate for a competition/season."""
    return json.dumps(best_home_record(_sd(), competition=competition, season=season,
                                       min_matches=min_matches), ensure_ascii=False, indent=2)


@mcp.tool()
def derbies_tool(season: Optional[int] = None) -> str:
    """Return traditional Brazilian derby matches, optionally in one season."""
    return json.dumps(derbies(_sd(), season=season), ensure_ascii=False, indent=2)


@mcp.tool()
def search_players_tool(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    limit: int = 50,
) -> str:
    """Search the FIFA player database by name/nationality/club/position/rating."""
    return json.dumps(search_players(
        _sd(), name=name, nationality=nationality, club=club, position=position,
        min_overall=min_overall, limit=limit,
    ), ensure_ascii=False, indent=2)


@mcp.tool()
def top_brazilian_players_tool(n: int = 10) -> str:
    """Return the top n Brazilian players by FIFA overall rating."""
    return json.dumps(top_brazilian_players(_sd(), n), ensure_ascii=False, indent=2)


@mcp.tool()
def players_at_club_tool(club: str, limit: int = 50) -> str:
    """Return all players at a given club (FIFA dataset)."""
    return json.dumps(players_at_club(_sd(), club, limit=limit), ensure_ascii=False, indent=2)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
