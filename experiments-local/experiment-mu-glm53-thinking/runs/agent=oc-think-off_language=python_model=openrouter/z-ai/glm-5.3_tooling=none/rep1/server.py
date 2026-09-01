"""Brazilian Soccer MCP server.

Run with:
    python server.py            # stdio transport (default)
    python server.py --http     # streamable HTTP on port 8000
"""

from __future__ import annotations

import argparse
import json
import sys

from mcp.server.mcpserver import MCPServer

from brazilian_soccer import (
    average_goals,
    biggest_wins,
    brazilian_club_summary,
    find_matches,
    head_to_head,
    load_data,
    search_players,
    standings,
    team_stats,
)

mcp = MCPServer(name="brazilian-soccer")

_data = load_data()


@mcp.tool()
def search_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    venue: str = "any",
    limit: int = 50,
) -> str:
    """Find matches by team, opponent, competition, season, or date range.

    Args:
        team: Team name (home, away, or either depending on venue).
        opponent: Restrict to matches against this opponent.
        competition: "Brasileirão", "Copa do Brasil", "Copa Libertadores", or exact tournament name.
        season: Year, e.g. 2023.
        date_from: Inclusive ISO date lower bound, e.g. "2023-01-01".
        date_to: Inclusive ISO date upper bound.
        venue: "any" (default), "home", or "away".
        limit: Max matches to return (default 50).
    """
    results = find_matches(
        _data, team, opponent, competition, season, date_from, date_to, venue, limit
    )
    return json.dumps({"count": len(results), "matches": results}, ensure_ascii=False)


@mcp.tool()
def get_team_stats(
    team: str,
    season: int | None = None,
    competition: str | None = None,
    venue: str = "any",
) -> str:
    """Win/loss/draw record, goals for/against, and home/away splits for a team."""
    return json.dumps(
        team_stats(_data, team, season, competition, venue), ensure_ascii=False
    )


@mcp.tool()
def compare_head_to_head(
    team: str,
    opponent: str,
    competition: str | None = None,
    limit: int = 200,
) -> str:
    """Head-to-head record between two teams across the whole dataset."""
    return json.dumps(
        head_to_head(_data, team, opponent, competition, limit), ensure_ascii=False
    )


@mcp.tool()
def get_standings(season: int, competition: str = "Brasileirão") -> str:
    """League table for a season, computed from match results (3 pts/win).

    The first row is the champion; the last four rows of a 20-team
    Brasileirão season are the relegated sides.
    """
    rows = standings(_data, season, competition)
    return json.dumps(
        {
            "season": season,
            "competition": competition,
            "champion": rows[0]["team"] if rows else None,
            "relegated": [r["team"] for r in rows[-4:]] if len(rows) >= 20 else [],
            "table": rows,
        },
        ensure_ascii=False,
    )


@mcp.tool()
def get_biggest_wins(
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> str:
    """Largest goal-margin victories in the dataset."""
    return json.dumps(
        biggest_wins(_data, competition, season, limit), ensure_ascii=False
    )


@mcp.tool()
def get_average_goals(
    competition: str | None = None,
    season: int | None = None,
) -> str:
    """Average goals per match plus home-win / away-win / draw rates."""
    return json.dumps(
        average_goals(_data, competition, season), ensure_ascii=False
    )


@mcp.tool()
def find_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    max_overall: int | None = None,
    limit: int = 25,
) -> str:
    """Search FIFA player data by name, nationality, club, position, or rating.

    Examples: nationality="Brazil"; club="Flamengo"; position="ST".
    Results are sorted by overall rating (best first).
    """
    results = search_players(
        _data,
        name=name,
        nationality=nationality,
        club=club,
        position=position,
        min_overall=min_overall,
        max_overall=max_overall,
        limit=limit,
    )
    return json.dumps({"count": len(results), "players": results}, ensure_ascii=False)


@mcp.tool()
def brazilian_clubs() -> str:
    """Squad size and average rating per Brazilian club (cross-file player+match query)."""
    return json.dumps(brazilian_club_summary(_data), ensure_ascii=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Brazilian Soccer MCP server")
    parser.add_argument("--http", action="store_true", help="serve over HTTP")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.http:
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        sys.exit(0)
